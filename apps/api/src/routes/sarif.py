"""SARIF 2.1.0 response formatter (Phase 8, T130).

Converts findings to SARIF 2.1.0 format for CI/CD integration.
"""

from __future__ import annotations

from typing import Any

SARIF_SCHEMA = "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json"


def findings_to_sarif(findings: list[dict[str, Any]], scan_id: str) -> dict[str, Any]:
    """Convert L1 findings list to SARIF 2.1.0 format.

    Args:
        findings: List of finding dictionaries from L1 scan
        scan_id: Unique scan identifier

    Returns:
        SARIF 2.1.0 compliant document
    """
    rules = []
    results = []
    seen_rules: set[str] = set()

    for f in findings:
        rule_id = f.get("rule_id", "unknown")
        if rule_id not in seen_rules:
            seen_rules.add(rule_id)
            rules.append(
                {
                    "id": rule_id,
                    "name": rule_id,
                    "shortDescription": {"text": f.get("message", "")},
                    "helpUri": f.get("incident_url", ""),
                }
            )
        results.append(
            {
                "ruleId": rule_id,
                "level": _severity_to_sarif_level(f.get("severity", "note")),
                "message": {"text": f.get("message", "")},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": f.get("file_path", "")},
                            "region": {
                                "startLine": f.get("start_line", 1),
                                "endLine": f.get("end_line", 1),
                            },
                        }
                    }
                ],
                "properties": {"remediation": f.get("remediation", "")},
            }
        )

    return {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "oute-muscle",
                        "version": "0.1.0",
                        "informationUri": "https://outemuscle.com",
                        "rules": rules,
                    }
                },
                "results": results,
                "properties": {"scanId": scan_id},
            }
        ],
    }


def _severity_to_sarif_level(severity: str) -> str:
    """Map oute-muscle severity to SARIF level.

    Args:
        severity: Severity level from finding

    Returns:
        SARIF level: error, warning, note
    """
    mapping = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}
    return mapping.get(severity.lower(), "note")
