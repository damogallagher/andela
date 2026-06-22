from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Any

from app.config import settings
from app.models import Finding, ScanRun
from app.scanner import RULES_BY_ID

SARIF_SCHEMA_URI = "https://json.schemastore.org/sarif-2.1.0.json"
SARIF_VERSION = "2.1.0"
TOOL_NAME = "Andela Enterprise Security Guardrail Auditor"
TOOL_INFORMATION_URI = "https://github.com/damogallagher/andela"
TOOL_VERSION = "0.1.0"

SEVERITY_LEVELS = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
}

SECURITY_SEVERITIES = {
    "critical": "9.5",
    "high": "8.0",
    "medium": "5.5",
    "low": "2.5",
}


def build_sarif(scan: ScanRun) -> dict[str, Any]:
    rules = _rules(scan.findings)
    rule_indexes = {rule["id"]: index for index, rule in enumerate(rules)}
    return {
        "$schema": SARIF_SCHEMA_URI,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": TOOL_NAME,
                        "informationUri": TOOL_INFORMATION_URI,
                        "semanticVersion": TOOL_VERSION,
                        "rules": rules,
                    }
                },
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "properties": {
                            "scanId": scan.id,
                            "scanLabel": scan.label,
                            "scanCreatedAt": scan.created_at.isoformat(),
                            "riskScore": scan.risk_score,
                        },
                    }
                ],
                "results": [_result(scan, finding, rule_indexes) for finding in scan.findings],
            }
        ],
    }


def _rules(findings: list[Finding]) -> list[dict[str, Any]]:
    first_by_rule: dict[str, Finding] = {}
    for finding in findings:
        first_by_rule.setdefault(finding.rule_id, finding)

    return [_rule(finding) for finding in sorted(first_by_rule.values(), key=lambda item: item.rule_id)]


def _rule(finding: Finding) -> dict[str, Any]:
    registry_rule = RULES_BY_ID.get(finding.rule_id)
    title = registry_rule.title if registry_rule else finding.title
    severity = registry_rule.severity if registry_rule else finding.severity.lower()
    description = registry_rule.description if registry_rule else finding.title
    recommendation = registry_rule.recommendation if registry_rule else finding.recommendation
    return {
        "id": finding.rule_id,
        "name": title,
        "shortDescription": {"text": title},
        "fullDescription": {"text": description},
        "help": {
            "text": recommendation,
            "markdown": recommendation,
        },
        "properties": {
            "problem.severity": severity,
            "security-severity": SECURITY_SEVERITIES.get(severity, "5.0"),
            "tags": ["security", "iac", severity],
        },
    }


def _result(scan: ScanRun, finding: Finding, rule_indexes: dict[str, int]) -> dict[str, Any]:
    severity = finding.severity.lower()
    return {
        "ruleId": finding.rule_id,
        "ruleIndex": rule_indexes[finding.rule_id],
        "level": SEVERITY_LEVELS.get(severity, "warning"),
        "message": {"text": f"{finding.title}: {finding.recommendation}"},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": _artifact_uri(scan, finding)},
                    "region": {"startLine": max(finding.line_number, 1)},
                },
                "logicalLocations": [{"fullyQualifiedName": finding.resource}],
            }
        ],
        "partialFingerprints": {
            "primaryLocationLineHash": _fingerprint(scan, finding),
        },
        "properties": {
            "severity": severity,
            "resource": finding.resource,
            "evidence": finding.evidence,
            "scanId": scan.id,
        },
    }


def _artifact_uri(scan: ScanRun, finding: Finding) -> str:
    finding_path = PurePosixPath(finding.file_path)
    target_path = Path(scan.target_path)

    if target_path.is_absolute():
        try:
            relative_target = target_path.resolve().relative_to(settings.app_scan_root.resolve())
        except ValueError:
            return finding_path.as_posix()

        if target_path.is_file():
            return relative_target.as_posix()
        return PurePosixPath(relative_target.as_posix(), finding_path).as_posix()

    return finding_path.as_posix()


def _fingerprint(scan: ScanRun, finding: Finding) -> str:
    raw_fingerprint = "|".join(
        [
            finding.rule_id,
            _artifact_uri(scan, finding),
            str(finding.line_number),
            finding.resource,
            finding.evidence,
        ]
    )
    return hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()[:32]
