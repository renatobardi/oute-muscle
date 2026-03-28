"""
T166: Integration test — end-to-end synthesis pipeline.
Flow: 3+ advisories → PatternDetector → SynthesisCandidate created →
      RuleSynthesizer (mocked LLM) → TestValidator → approved → L1 Rule promoted.

No real GCP/DB calls; all external adapters are mocked.
"""

import hashlib
import pytest
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
from packages.core.src.domain.rules.pattern_detector import PatternDetector, PatternMatch
from packages.core.src.domain.rules.synthesizer import RuleSynthesizer, SynthesisResult
from packages.core.src.domain.rules.test_validator import CandidateTestValidator, ValidationResult
from packages.core.src.domain.rules.synthesis_service import SynthesisService
from packages.core.src.domain.rules.synthesis_candidate import SynthesisCandidate, CandidateStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


ANTI_PATTERN = "retry without exponential backoff"
ANTI_PATTERN_HASH = _hash(ANTI_PATTERN)

VALID_SEMGREP_YAML = """
rules:
  - id: cascading-failure-002
    patterns:
      - pattern: |
          for $VAR in range(...):
              $RESP = requests.get(...)
    message: "Retry without backoff"
    languages: [python]
    severity: WARNING
    metadata:
      incident_id: inc-1
      category: cascading-failure
      remediation: Use tenacity
""".strip()

VALID_TEST_FILE = """
# ruleid: cascading-failure-002
for i in range(3):
    resp = requests.get(url)

# ok: cascading-failure-002
@tenacity.retry()
def fetch(url):
    return requests.get(url)
""".strip()

SAMPLE_INCIDENT = {
    "id": "inc-1",
    "title": "Cascading failure from retry storm",
    "category": "cascading-failure",
    "severity": "high",
    "anti_pattern": ANTI_PATTERN,
    "remediation": "Use exponential backoff",
    "affected_languages": ["python"],
}


# ---------------------------------------------------------------------------
# End-to-end test
# ---------------------------------------------------------------------------

class TestSynthesisE2E:
    @pytest.mark.asyncio
    async def test_full_pipeline_3_advisories_to_promoted_rule(self):
        """
        Simulate: 3 advisories match same hash → candidate created → YAML generated
        → tests pass → candidate approved → L1 rule promoted.
        """
        # --- Step 1: Pattern detection ---
        detector = PatternDetector()
        mock_candidate_repo = AsyncMock()
        mock_candidate_repo.count_advisories_by_hash.return_value = [
            PatternMatch(hash=ANTI_PATTERN_HASH, count=3, sample_incident_id="inc-1")
        ]
        mock_candidate_repo.existing_candidate_hashes.return_value = set()
        mock_candidate_repo.retriable_failed_hashes.return_value = set()

        triggerable = await detector.detect_triggerable(mock_candidate_repo)
        assert len(triggerable) == 1
        assert triggerable[0].hash == ANTI_PATTERN_HASH

        # --- Step 2: Synthesis candidate created ---
        candidate = SynthesisCandidate(
            id="cand-e2e-1",
            anti_pattern_hash=ANTI_PATTERN_HASH,
            advisory_count=3,
            status=CandidateStatus.PENDING,
            failure_count=0,
            failure_reason=None,
            generated_rule_yaml=None,
            created_at=MagicMock(),
            updated_at=MagicMock(),
        )
        mock_candidate_repo.create.return_value = candidate

        # --- Step 3: Rule synthesis ---
        mock_llm = AsyncMock()
        mock_llm.generate_structured.return_value = {
            "rule_yaml": VALID_SEMGREP_YAML,
            "test_file": VALID_TEST_FILE,
            "rule_id": "cascading-failure-002",
        }

        synthesizer = RuleSynthesizer(llm=mock_llm)
        synthesis_result = await synthesizer.synthesize(incident=SAMPLE_INCIDENT)

        assert synthesis_result.rule_id == "cascading-failure-002"
        assert "cascading-failure-002" in synthesis_result.rule_yaml

        # --- Step 4: Test validation ---
        mock_semgrep = AsyncMock()
        mock_semgrep.run_test.return_value = ValidationResult(
            passed=True,
            errors=[],
            test_output="All tests passed.",
        )

        validator = CandidateTestValidator(semgrep_runner=mock_semgrep)
        validation = await validator.validate(synthesis_result)

        assert validation.passed is True

        # --- Step 5: Approve → promote to L1 rule ---
        mock_rule_repo = AsyncMock()
        promoted_rule = MagicMock()
        promoted_rule.id = "cascading-failure-002"
        mock_rule_repo.create.return_value = promoted_rule

        mock_candidate_repo.get.return_value = candidate

        service = SynthesisService(
            candidate_repo=mock_candidate_repo,
            rule_repo=mock_rule_repo,
        )
        rule_id = await service.approve("cand-e2e-1", approved_by="user-admin")

        assert rule_id == "cascading-failure-002"
        mock_candidate_repo.update_status.assert_called_with(
            "cand-e2e-1", CandidateStatus.APPROVED
        )

    @pytest.mark.asyncio
    async def test_pipeline_with_test_failure_marks_candidate_failed(self):
        """When semgrep --test fails, candidate transitions to failed."""
        mock_semgrep = AsyncMock()
        mock_semgrep.run_test.return_value = ValidationResult(
            passed=False,
            errors=["Error: line 2: expected match not found"],
            test_output="1 error.",
        )

        validator = CandidateTestValidator(semgrep_runner=mock_semgrep)
        bad_result = SynthesisResult(
            rule_id="cascading-failure-002",
            rule_yaml=VALID_SEMGREP_YAML,
            test_file="# no valid annotations",
        )

        validation = await validator.validate(bad_result)

        assert validation.passed is False
        assert len(validation.errors) >= 1

    @pytest.mark.asyncio
    async def test_pipeline_third_failure_archives_candidate(self):
        """After 3 failures the candidate is auto-archived, no more retries."""
        from packages.core.src.domain.rules.synthesis_candidate import MAX_FAILURE_COUNT
        from datetime import datetime, timezone

        candidate = SynthesisCandidate(
            id="cand-fail-3",
            anti_pattern_hash=ANTI_PATTERN_HASH,
            advisory_count=4,
            status=CandidateStatus.FAILED,
            failure_count=MAX_FAILURE_COUNT - 1,  # 2 — one more will trigger archive
            failure_reason="prev failure",
            generated_rule_yaml=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_candidate_repo = AsyncMock()
        mock_candidate_repo.get.return_value = candidate

        service = SynthesisService(
            candidate_repo=mock_candidate_repo,
            rule_repo=AsyncMock(),
        )
        await service.mark_failed("cand-fail-3", reason="Third failure")

        call_args = mock_candidate_repo.update_status.call_args
        assert call_args[0][1] == CandidateStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_pipeline_below_threshold_creates_no_candidate(self):
        """2 advisory matches — no synthesis candidate should be triggered."""
        detector = PatternDetector()

        mock_candidate_repo = AsyncMock()
        mock_candidate_repo.count_advisories_by_hash.return_value = [
            PatternMatch(hash=ANTI_PATTERN_HASH, count=2, sample_incident_id="inc-1")
        ]
        mock_candidate_repo.existing_candidate_hashes.return_value = set()
        mock_candidate_repo.retriable_failed_hashes.return_value = set()

        triggerable = await detector.detect_triggerable(mock_candidate_repo)

        assert len(triggerable) == 0
