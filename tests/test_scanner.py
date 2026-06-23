from collections import Counter
from pathlib import Path

from app.scanner import (
    RULES,
    RULES_BY_ID,
    FindingCandidate,
    ScanInputFile,
    calculate_risk_score,
    scan_files,
    scan_path,
)

SCENARIOS = Path("sample_iac/scenarios")


def make_finding(severity: str, index: int, resource: str = "shared-resource") -> FindingCandidate:
    return FindingCandidate(
        rule_id=f"SYNTHETIC_{index}",
        title=f"Synthetic {severity} finding",
        severity=severity,
        file_path="synthetic.tf",
        line_number=index + 1,
        resource=resource,
        evidence="synthetic evidence",
        recommendation="synthetic recommendation",
    )


def rule_counts(path: Path) -> Counter:
    result = scan_path(path)
    return Counter(finding.rule_id for finding in result.findings)


def test_rule_registry_contains_metadata_and_check_functions() -> None:
    core_rule_ids = [
        "OPEN_SSH_INGRESS",
        "HARDCODED_SECRET",
        "S3_PUBLIC_ACL",
        "IAM_WILDCARD_POLICY",
        "DATABASE_ENCRYPTION_DISABLED",
        "S3_VERSIONING_DISABLED",
    ]
    assert [rule.rule_id for rule in RULES[: len(core_rule_ids)]] == core_rule_ids
    assert len(RULES) >= 100
    assert set(RULES_BY_ID) == {rule.rule_id for rule in RULES}
    assert len(RULES_BY_ID) == len(RULES)
    assert "AWS_CLOUDTRAIL_ENABLE_LOGGING_DISABLED" in RULES_BY_ID
    assert "AZURE_STORAGE_ACCOUNT_ENABLE_HTTPS_TRAFFIC_ONLY_DISABLED" in RULES_BY_ID
    assert "AZURE_KUBERNETES_CLUSTER_ROLE_BASED_ACCESS_CONTROL_ENABLED_DISABLED" in RULES_BY_ID
    assert all(rule.title and rule.severity and rule.description and rule.recommendation for rule in RULES)
    assert all(callable(rule.check) for rule in RULES)


def test_catalog_detects_representative_aws_and_azure_vulnerabilities() -> None:
    result = scan_files(
        [
            ScanInputFile(
                file_path="catalog_rules.tf",
                content="""
resource "aws_cloudtrail" "audit" {
  enable_logging = false
}

resource "aws_ebs_volume" "data" {
  encrypted = false
}

resource "azurerm_storage_account" "logs" {
  enable_https_traffic_only = false
  min_tls_version = "TLS1_0"
}

resource "azurerm_kubernetes_cluster" "aks" {
  role_based_access_control_enabled = false
}
""",
            )
        ],
        "uploaded: catalog_rules.tf",
    )

    assert Counter(finding.rule_id for finding in result.findings) == Counter(
        {
            "AWS_CLOUDTRAIL_ENABLE_LOGGING_DISABLED": 1,
            "AWS_EBS_VOLUME_ENCRYPTED_DISABLED": 1,
            "AZURE_STORAGE_ACCOUNT_ENABLE_HTTPS_TRAFFIC_ONLY_DISABLED": 1,
            "AZURE_STORAGE_ACCOUNT_MIN_TLS_VERSION_WEAK_TLS": 1,
            "AZURE_KUBERNETES_CLUSTER_ROLE_BASED_ACCESS_CONTROL_ENABLED_DISABLED": 1,
        }
    )


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
    assert result.risk_score == 60


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
    assert result.risk_score == 73


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
    for finding in result.findings:
        rule = RULES_BY_ID[finding.rule_id]
        assert finding.title == rule.title
        assert finding.severity == rule.severity
        assert finding.recommendation == rule.recommendation
    assert result.risk_score == 60


def test_clean_scenario_has_full_score() -> None:
    result = scan_path(SCENARIOS / "clean")

    assert result.files_scanned == 2
    assert result.findings == []
    assert result.risk_score == 100


def test_large_violations_scenario_exercises_all_severity_categories() -> None:
    result = scan_path(SCENARIOS / "large_violations")

    assert result.files_scanned == 2
    assert Counter(finding.severity for finding in result.findings) == Counter(
        {
            "critical": 24,
            "high": 12,
            "medium": 12,
            "low": 12,
        }
    )
    assert Counter(finding.rule_id for finding in result.findings) == Counter(
        {
            "OPEN_SSH_INGRESS": 12,
            "HARDCODED_SECRET": 12,
            "S3_PUBLIC_ACL": 12,
            "DATABASE_ENCRYPTION_DISABLED": 12,
            "S3_VERSIONING_DISABLED": 12,
        }
    )
    assert result.risk_score == 42


def test_all_sample_iac_scenarios_are_scanned_together() -> None:
    result = scan_path(Path("sample_iac"))

    assert result.files_scanned == 10
    assert Counter(finding.rule_id for finding in result.findings) == Counter(
        {
            "OPEN_SSH_INGRESS": 14,
            "HARDCODED_SECRET": 12,
            "S3_PUBLIC_ACL": 14,
            "DATABASE_ENCRYPTION_DISABLED": 14,
            "IAM_WILDCARD_POLICY": 1,
            "S3_VERSIONING_DISABLED": 12,
        }
    )
    assert result.risk_score == 47


def test_scan_files_supports_uploaded_in_memory_content() -> None:
    result = scan_files(
        [
            ScanInputFile(
                file_path="uploaded_security_group.tf",
                content="""
resource "aws_security_group" "admin" {
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
""",
            )
        ],
        "uploaded: uploaded_security_group.tf",
    )

    assert result.target_path == "uploaded: uploaded_security_group.tf"
    assert result.files_scanned == 1
    assert result.risk_score == 55
    assert result.findings[0].rule_id == "OPEN_SSH_INGRESS"


def test_scan_files_detects_and_redacts_hardcoded_secrets() -> None:
    aws_access_key = "AKIA" + ("0" * 16)
    result = scan_files(
        [
            ScanInputFile(
                file_path="uploaded_secrets.tf",
                content=f"""
provider "aws" {{
  access_key = "{aws_access_key}"
  secret_key = var.aws_secret_key
}}

resource "null_resource" "app_config" {{
  triggers = {{
    admin_password = "example-password-01"
    api_token      = "${{var.api_token}}"
  }}
}}
""",
            )
        ],
        "uploaded: uploaded_secrets.tf",
    )

    assert Counter(finding.rule_id for finding in result.findings) == Counter({"HARDCODED_SECRET": 2})
    assert all(finding.severity == "critical" for finding in result.findings)
    assert {finding.evidence for finding in result.findings} == {
        'access_key = "AKIA****************"',
        "admin_password = <redacted>",
    }
    assert all(aws_access_key not in finding.evidence for finding in result.findings)
    assert all("example-password-01" not in finding.evidence for finding in result.findings)


def test_risk_score_uses_weighted_density_without_zero_saturation() -> None:
    four_critical_findings = [make_finding("critical", index) for index in range(4)]
    ten_critical_findings = [make_finding("critical", index) for index in range(10)]

    four_critical_score = calculate_risk_score(four_critical_findings, files_scanned=1)
    ten_critical_score = calculate_risk_score(ten_critical_findings, files_scanned=1)
    broader_scope_score = calculate_risk_score(four_critical_findings, files_scanned=20)

    assert calculate_risk_score([], files_scanned=20) == 100
    assert 0 < ten_critical_score < four_critical_score < 100
    assert broader_scope_score > four_critical_score
