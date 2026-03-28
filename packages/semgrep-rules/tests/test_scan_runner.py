"""Integration test for Semgrep scan runner — verifies SARIF output format.

T038: Requires semgrep installed. Skipped automatically if not available.
Run: pytest packages/semgrep-rules/tests/ -v
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

RULES_DIR = Path(__file__).parent.parent / "rules"


def _semgrep_available() -> bool:
    try:
        subprocess.run(["semgrep", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@pytest.fixture
def vulnerable_py(tmp_path: Path) -> Path:
    content = (
        "import re\n"
        "import requests\n\n"
        "# Unsafe regex\n"
        'pattern = re.compile(r"(a+)+b")\n\n'
        "# Missing timeout\n"
        'response = requests.get("https://api.example.com/data")\n'
    )
    f = tmp_path / "vulnerable.py"
    f.write_text(content)
    return f


@pytest.mark.skipif(not _semgrep_available(), reason="semgrep not installed")
def test_scan_produces_sarif(vulnerable_py: Path) -> None:
    result = subprocess.run(
        ["semgrep", "--config", str(RULES_DIR), "--sarif", str(vulnerable_py)],
        capture_output=True,
        text=True,
    )
    sarif = json.loads(result.stdout)
    assert sarif.get("version") == "2.1.0"
    assert "runs" in sarif


@pytest.mark.skipif(not _semgrep_available(), reason="semgrep not installed")
def test_unsafe_regex_rule_fires(vulnerable_py: Path) -> None:
    result = subprocess.run(
        [
            "semgrep",
            "--config", str(RULES_DIR / "unsafe-regex"),
            "--json",
            str(vulnerable_py),
        ],
        capture_output=True,
        text=True,
    )
    output = json.loads(result.stdout)
    rule_ids = [r["check_id"] for r in output.get("results", [])]
    assert "unsafe-regex-001" in rule_ids
