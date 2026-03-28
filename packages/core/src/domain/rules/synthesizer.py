"""
T168: Rule synthesis service.

Calls the LLM to generate:
  1. A valid Semgrep YAML rule with incident metadata.
  2. A test file with ``# ruleid: <id>`` (positive) and ``# ok: <id>`` (negative) annotations.

Validates the output before returning so callers can trust the result is
structurally correct (YAML parses, has 'rules' key, test annotations present).
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Protocol

import yaml

# ---------------------------------------------------------------------------
# Result / error types
# ---------------------------------------------------------------------------


@dataclass
class SynthesisResult:
    rule_id: str
    rule_yaml: str
    test_file: str


class SynthesisError(Exception):
    """Raised when synthesis fails for any reason (LLM error, invalid output)."""


# ---------------------------------------------------------------------------
# LLM Port (injected)
# ---------------------------------------------------------------------------


class LLMPort(Protocol):
    async def generate_structured(self, prompt: str, schema: dict) -> dict: ...


# ---------------------------------------------------------------------------
# Synthesis prompt
# ---------------------------------------------------------------------------

_SYNTHESIS_PROMPT_TEMPLATE = textwrap.dedent(
    """\
    You are an expert Semgrep rule author. Given the following production incident,
    generate a Semgrep rule that would statically detect the anti-pattern described.

    ## Incident
    Title:           {title}
    Category:        {category}
    Severity:        {severity}
    Anti-pattern:    {anti_pattern}
    Remediation:     {remediation}
    Languages:       {languages}
    Code example:    {code_example}
    Incident ID:     {incident_id}

    ## Requirements
    1. Return valid Semgrep YAML with a `rules:` list containing exactly one rule.
    2. The rule ID must follow the format `{category}-NNN` (e.g. `cascading-failure-002`).
    3. Include `metadata.incident_id`, `metadata.category`, and `metadata.remediation`.
    4. Return a test file with:
       - At least one `# ruleid: <id>` annotation above a code block that SHOULD match.
       - At least one `# ok: <id>` annotation above a code block that should NOT match.
    5. The YAML `languages:` list must match the incident's affected languages.

    Respond with JSON: {{
      "rule_yaml": "<the full YAML string>",
      "test_file": "<the full test file string>",
      "rule_id":   "<the rule ID string>"
    }}
    """
)

_SYNTHESIS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "rule_yaml": {"type": "string"},
        "test_file": {"type": "string"},
        "rule_id": {"type": "string"},
    },
    "required": ["rule_yaml", "test_file", "rule_id"],
}


# ---------------------------------------------------------------------------
# Synthesizer service
# ---------------------------------------------------------------------------


class RuleSynthesizer:
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def synthesize(self, incident: dict) -> SynthesisResult:
        """
        Generate a Semgrep rule and test file for the given incident dict.
        Raises SynthesisError on any failure.
        """
        prompt = _SYNTHESIS_PROMPT_TEMPLATE.format(
            title=incident.get("title", ""),
            category=incident.get("category", ""),
            severity=incident.get("severity", ""),
            anti_pattern=incident.get("anti_pattern", ""),
            remediation=incident.get("remediation", ""),
            languages=", ".join(incident.get("affected_languages", [])),
            code_example=incident.get("code_example", "N/A"),
            incident_id=incident.get("id", ""),
        )

        try:
            response = await self._llm.generate_structured(
                prompt=prompt,
                schema=_SYNTHESIS_RESPONSE_SCHEMA,
            )
        except Exception as exc:
            raise SynthesisError(f"LLM call failed: {exc}") from exc

        rule_yaml: str = response.get("rule_yaml", "")
        test_file: str = response.get("test_file", "")
        rule_id: str = response.get("rule_id", "")

        self._validate_yaml(rule_yaml, incident.get("id", ""))
        self._validate_test_file(test_file, rule_id)

        return SynthesisResult(
            rule_id=rule_id,
            rule_yaml=rule_yaml,
            test_file=test_file,
        )

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_yaml(self, rule_yaml: str, incident_id: str) -> None:
        """Parse YAML and assert it has the expected Semgrep structure."""
        try:
            parsed = yaml.safe_load(rule_yaml)
        except yaml.YAMLError as exc:
            raise SynthesisError(f"Invalid YAML returned by LLM: {exc}") from exc

        if not isinstance(parsed, dict) or "rules" not in parsed:
            raise SynthesisError("Invalid Semgrep YAML: missing top-level 'rules' key.")

        rules = parsed["rules"]
        if not isinstance(rules, list) or len(rules) == 0:
            raise SynthesisError("Invalid Semgrep YAML: 'rules' list is empty.")

        rule = rules[0]
        for required_key in ("id", "message", "languages", "severity"):
            if required_key not in rule:
                raise SynthesisError(
                    f"Invalid Semgrep YAML: rule missing required field '{required_key}'."
                )

    def _validate_test_file(self, test_file: str, rule_id: str) -> None:
        """Verify the test file has both ruleid and ok annotations for the rule ID."""
        if not rule_id:
            return  # can't validate without a rule ID

        ruleid_pattern = f"# ruleid: {rule_id}"
        ok_pattern = f"# ok: {rule_id}"

        if ruleid_pattern not in test_file:
            raise SynthesisError(f"Test file missing '# ruleid: {rule_id}' annotation.")
        if ok_pattern not in test_file:
            raise SynthesisError(f"Test file missing '# ok: {rule_id}' annotation.")
