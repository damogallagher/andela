from collections import Counter
from pathlib import Path

from app.scanner import calculate_risk_score, scan_path


SCENARIOS = Path("sample_iac/scenarios")


def rule_counts(path: Path) -> Counter:
    result = scan_path(path)
    return Counter(finding.rule_id for finding in result.findings)


def test_both_risky_scenario_detects_terraform_and_json_findings() -> None:
    result = scan_path(SCENARIOS / "both_risky")

    assert result.files_scanned == 2
    assert Counter(finding.rule_id for finding in result.findings) == Counter(
        {
            "OPEN_SSH_INGRESS": 1,
            "S3_PUBLIC_ACL": 1,
            "DATABASE_ENCRYPTION_DISABLED": 1,
        }
    )
    assert result.findings[0].rule_id == "OPEN_SSH_INGRESS"
    assert result.risk_score == 40


def test_terraform_only_scenario_detects_only_terraform_findings() -> None:
    result = scan_path(SCENARIOS / "terraform_only")

    assert result.files_scanned == 2
    assert Counter(finding.rule_id for finding in result.findings) == Counter(
        {
            "S3_PUBLIC_ACL": 1,
            "DATABASE_ENCRYPTION_DISABLED": 1,
        }
    )
    assert {finding.file_path for finding in result.findings} == {"risky_terraform.tf"}
    assert result.risk_score == 70


def test_json_only_scenario_detects_only_json_findings() -> None:
    result = scan_path(SCENARIOS / "json_only")

    assert result.files_scanned == 2
    assert Counter(finding.rule_id for finding in result.findings) == Counter(
        {
            "OPEN_SSH_INGRESS": 1,
            "IAM_WILDCARD_POLICY": 1,
        }
    )
    assert {finding.file_path for finding in result.findings} == {"risky_cloudformation.json"}
    assert result.risk_score == 50


def test_clean_scenario_has_full_score() -> None:
    result = scan_path(SCENARIOS / "clean")

    assert result.files_scanned == 2
    assert result.findings == []
    assert result.risk_score == 100


def test_all_sample_iac_scenarios_are_scanned_together() -> None:
    result = scan_path(Path("sample_iac"))

    assert result.files_scanned == 8
    assert Counter(finding.rule_id for finding in result.findings) == Counter(
        {
            "OPEN_SSH_INGRESS": 2,
            "S3_PUBLIC_ACL": 2,
            "DATABASE_ENCRYPTION_DISABLED": 2,
            "IAM_WILDCARD_POLICY": 1,
        }
    )
    assert result.risk_score == 0


def test_risk_score_never_goes_below_zero() -> None:
    result = scan_path(Path("sample_iac"))
    overloaded_findings = result.findings * 10

    assert calculate_risk_score(overloaded_findings) == 0

