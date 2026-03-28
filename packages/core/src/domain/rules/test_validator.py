"""
T169: Candidate test validator.

Runs ``semgrep --test`` against the generated rule YAML and test file in a
temporary directory. Transitions the candidate to 'failed' if tests fail.
"""

from __future__ import annotations

import asyncio
import tempfile
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from packages.core.src.domain.rules.synthesizer import SynthesisResult


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    test_output: str = ""


# ---------------------------------------------------------------------------
# Semgrep runner Protocol (injectable / mockable)
# ---------------------------------------------------------------------------

class SemgrepRunnerPort(Protocol):
    async def run_test(
        self,
        rule_yaml: str,
        test_file: str,
        rule_id: str,
    ) -> ValidationResult:
        ...


# ---------------------------------------------------------------------------
# Default runner: shells out to `semgrep --test`
# ---------------------------------------------------------------------------

class SubprocessSemgrepRunner:
    """Runs semgrep --test in a temp directory via asyncio subprocess."""

    async def run_test(
        self,
        rule_yaml: str,
        test_file: str,
        rule_id: str,
    ) -> ValidationResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            rule_path = Path(tmpdir) / f"{rule_id}.yaml"
            test_path = Path(tmpdir) / f"{rule_id}.test.py"

            rule_path.write_text(rule_yaml, encoding="utf-8")
            test_path.write_text(test_file, encoding="utf-8")

            proc = await asyncio.create_subprocess_exec(
                "semgrep",
                "--test",
                str(tmpdir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
            output = stdout.decode() + stderr.decode()

            if proc.returncode == 0:
                return ValidationResult(passed=True, test_output=output)
            else:
                errors = [
                    line
                    for line in output.splitlines()
                    if "error" in line.lower() or "fail" in line.lower()
                ]
                return ValidationResult(passed=False, errors=errors, test_output=output)


# ---------------------------------------------------------------------------
# Validator service
# ---------------------------------------------------------------------------

class CandidateTestValidator:
    """
    Wraps the semgrep runner; used by the synthesis worker to validate a
    generated rule before opening the PR.
    """

    def __init__(self, semgrep_runner: SemgrepRunnerPort | None = None) -> None:
        self._runner = semgrep_runner or SubprocessSemgrepRunner()

    async def validate(self, result: SynthesisResult) -> ValidationResult:
        """
        Validate the synthesis result by running semgrep --test.
        Returns a ValidationResult; never raises — failures are encoded in the result.
        """
        try:
            return await self._runner.run_test(
                rule_yaml=result.rule_yaml,
                test_file=result.test_file,
                rule_id=result.rule_id,
            )
        except asyncio.TimeoutError:
            return ValidationResult(
                passed=False,
                errors=["semgrep --test timed out after 60s"],
                test_output="",
            )
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(
                passed=False,
                errors=[f"Unexpected error running semgrep: {exc}"],
                test_output="",
            )
