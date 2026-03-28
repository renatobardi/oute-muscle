"""
T164: Unit tests for rule generation service.
The LLM produces valid Semgrep YAML + a test file.
"""

from unittest.mock import AsyncMock

import pytest
import yaml

from packages.core.src.domain.rules.synthesizer import (
    RuleSynthesizer,
    SynthesisError,
    SynthesisResult,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_INCIDENT = {
    "id": "inc-1",
    "title": "Retry without exponential backoff caused cascading failure",
    "category": "cascading-failure",
    "severity": "high",
    "anti_pattern": "Retrying a failed request immediately without any backoff or jitter",
    "remediation": "Use exponential backoff with jitter (e.g. tenacity library)",
    "affected_languages": ["python"],
    "code_example": "for _ in range(3):\n    resp = requests.get(url)\n    if resp.ok:\n        break",
}

VALID_SEMGREP_YAML = """
rules:
  - id: cascading-failure-002
    patterns:
      - pattern: |
          for $VAR in range(...):
              $RESP = requests.get(...)
    message: "Retry without backoff detected. Use exponential backoff."
    languages: [python]
    severity: WARNING
    metadata:
      incident_id: inc-1
      category: cascading-failure
      remediation: Use tenacity with exponential backoff
""".strip()

VALID_TEST_FILE = """
# ruleid: cascading-failure-002
for i in range(3):
    resp = requests.get(url)
    if resp.ok:
        break

# ok: cascading-failure-002
import tenacity
@tenacity.retry(wait=tenacity.wait_exponential())
def fetch(url):
    return requests.get(url)
""".strip()


# ---------------------------------------------------------------------------
# Tests: RuleSynthesizer.synthesize
# ---------------------------------------------------------------------------


class TestRuleSynthesizer:
    @pytest.mark.asyncio
    async def test_returns_synthesis_result_with_yaml_and_test_file(self):
        mock_llm = AsyncMock()
        mock_llm.generate_structured.return_value = {
            "rule_yaml": VALID_SEMGREP_YAML,
            "test_file": VALID_TEST_FILE,
            "rule_id": "cascading-failure-002",
        }

        synthesizer = RuleSynthesizer(llm=mock_llm)
        result = await synthesizer.synthesize(incident=SAMPLE_INCIDENT)

        assert isinstance(result, SynthesisResult)
        assert result.rule_yaml == VALID_SEMGREP_YAML
        assert result.test_file == VALID_TEST_FILE
        assert result.rule_id == "cascading-failure-002"

    @pytest.mark.asyncio
    async def test_generated_yaml_is_valid_semgrep_schema(self):
        """The YAML must parse and have a 'rules' key with at least one entry."""
        mock_llm = AsyncMock()
        mock_llm.generate_structured.return_value = {
            "rule_yaml": VALID_SEMGREP_YAML,
            "test_file": VALID_TEST_FILE,
            "rule_id": "cascading-failure-002",
        }

        synthesizer = RuleSynthesizer(llm=mock_llm)
        result = await synthesizer.synthesize(incident=SAMPLE_INCIDENT)

        parsed = yaml.safe_load(result.rule_yaml)
        assert "rules" in parsed
        assert len(parsed["rules"]) >= 1
        rule = parsed["rules"][0]
        assert "id" in rule
        assert "message" in rule
        assert "languages" in rule
        assert "severity" in rule

    @pytest.mark.asyncio
    async def test_rule_id_follows_category_sequence_format(self):
        """Rule ID must match pattern {category}-{NNN}."""
        mock_llm = AsyncMock()
        mock_llm.generate_structured.return_value = {
            "rule_yaml": VALID_SEMGREP_YAML,
            "test_file": VALID_TEST_FILE,
            "rule_id": "cascading-failure-002",
        }

        synthesizer = RuleSynthesizer(llm=mock_llm)
        result = await synthesizer.synthesize(incident=SAMPLE_INCIDENT)

        import re

        assert re.match(r"^[a-z-]+-\d{3}$", result.rule_id), (
            f"Rule ID '{result.rule_id}' does not match {{category}}-{{NNN}} format"
        )

    @pytest.mark.asyncio
    async def test_raises_synthesis_error_on_llm_failure(self):
        mock_llm = AsyncMock()
        mock_llm.generate_structured.side_effect = RuntimeError("LLM timeout")

        synthesizer = RuleSynthesizer(llm=mock_llm)

        with pytest.raises(SynthesisError) as exc:
            await synthesizer.synthesize(incident=SAMPLE_INCIDENT)

        assert "LLM" in str(exc.value) or "timeout" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_raises_synthesis_error_on_invalid_yaml(self):
        """If LLM returns malformed YAML, SynthesisError is raised."""
        mock_llm = AsyncMock()
        mock_llm.generate_structured.return_value = {
            "rule_yaml": "this: is: not: valid: yaml: ::::",
            "test_file": VALID_TEST_FILE,
            "rule_id": "cascading-failure-002",
        }

        synthesizer = RuleSynthesizer(llm=mock_llm)

        with pytest.raises(SynthesisError) as exc:
            await synthesizer.synthesize(incident=SAMPLE_INCIDENT)

        assert "yaml" in str(exc.value).lower() or "invalid" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_raises_synthesis_error_when_yaml_missing_rules_key(self):
        bad_yaml = "id: broken-rule\nmessage: no rules wrapper"
        mock_llm = AsyncMock()
        mock_llm.generate_structured.return_value = {
            "rule_yaml": bad_yaml,
            "test_file": VALID_TEST_FILE,
            "rule_id": "broken-rule",
        }

        synthesizer = RuleSynthesizer(llm=mock_llm)

        with pytest.raises(SynthesisError):
            await synthesizer.synthesize(incident=SAMPLE_INCIDENT)

    @pytest.mark.asyncio
    async def test_includes_incident_metadata_in_rule(self):
        """Generated rule must carry incident_id in metadata."""
        mock_llm = AsyncMock()
        mock_llm.generate_structured.return_value = {
            "rule_yaml": VALID_SEMGREP_YAML,
            "test_file": VALID_TEST_FILE,
            "rule_id": "cascading-failure-002",
        }

        synthesizer = RuleSynthesizer(llm=mock_llm)
        result = await synthesizer.synthesize(incident=SAMPLE_INCIDENT)

        parsed = yaml.safe_load(result.rule_yaml)
        metadata = parsed["rules"][0].get("metadata", {})
        assert metadata.get("incident_id") == "inc-1"

    @pytest.mark.asyncio
    async def test_test_file_contains_ruleid_annotation(self):
        """Test file must contain '# ruleid: <id>' for semgrep --test to work."""
        mock_llm = AsyncMock()
        mock_llm.generate_structured.return_value = {
            "rule_yaml": VALID_SEMGREP_YAML,
            "test_file": VALID_TEST_FILE,
            "rule_id": "cascading-failure-002",
        }

        synthesizer = RuleSynthesizer(llm=mock_llm)
        result = await synthesizer.synthesize(incident=SAMPLE_INCIDENT)

        assert f"# ruleid: {result.rule_id}" in result.test_file

    @pytest.mark.asyncio
    async def test_test_file_contains_ok_annotation(self):
        """Test file must contain '# ok: <id>' for the negative (safe) example."""
        mock_llm = AsyncMock()
        mock_llm.generate_structured.return_value = {
            "rule_yaml": VALID_SEMGREP_YAML,
            "test_file": VALID_TEST_FILE,
            "rule_id": "cascading-failure-002",
        }

        synthesizer = RuleSynthesizer(llm=mock_llm)
        result = await synthesizer.synthesize(incident=SAMPLE_INCIDENT)

        assert f"# ok: {result.rule_id}" in result.test_file

    @pytest.mark.asyncio
    async def test_prompt_includes_incident_anti_pattern_and_remediation(self):
        """The LLM prompt must include key incident fields for quality generation."""
        mock_llm = AsyncMock()
        mock_llm.generate_structured.return_value = {
            "rule_yaml": VALID_SEMGREP_YAML,
            "test_file": VALID_TEST_FILE,
            "rule_id": "cascading-failure-002",
        }

        synthesizer = RuleSynthesizer(llm=mock_llm)
        await synthesizer.synthesize(incident=SAMPLE_INCIDENT)

        call_args = mock_llm.generate_structured.call_args
        prompt = str(call_args)
        assert "Retrying a failed request" in prompt or "anti_pattern" in prompt
