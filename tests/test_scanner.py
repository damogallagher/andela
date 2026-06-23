from collections import Counter
from pathlib import Path

from app.scanner import (
    RULES,
    RULES_BY_ID,
    FindingCandidate,
    ScanContext,
    ScanInputFile,
    _iter_json_resources,
    _json_key_line,
    _line_at,
    _provider_neutral_resource,
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


def test_unsupported_single_file_scan_returns_empty_result(tmp_path: Path) -> None:
    notes = tmp_path / "notes.txt"
    notes.write_text("not infrastructure", encoding="utf-8")

    result = scan_path(notes)

    assert result.files_scanned == 0
    assert result.findings == []
    assert result.risk_score == 100


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


def test_scan_files_handles_invalid_and_unusual_json_shapes() -> None:
    result = scan_files(
        [
            ScanInputFile(file_path="broken.json", content="{not json"),
            ScanInputFile(file_path="array.json", content='["not", "resources"]'),
            ScanInputFile(
                file_path="odd.template",
                content="""
{
  "Resources": {
    "BadResource": "not an object",
    "Bucket": {
      "Type": "AWS::S3::Bucket",
      "Properties": "not an object"
    },
    "VersionedBucket": {
      "Type": "AWS::S3::Bucket",
      "Properties": {
        "VersioningConfiguration": "Suspended"
      }
    }
  }
}
""",
            ),
        ],
        "uploaded: unusual-json",
    )

    assert result.files_scanned == 3
    assert result.findings == []
    assert result.risk_score == 100


def test_json_rules_handle_policy_lists_ingress_dicts_and_invalid_ports() -> None:
    result = scan_files(
        [
            ScanInputFile(
                file_path="policy-list.json",
                content="""
{
  "Resources": {
    "AdminRole": {
      "Type": "AWS::IAM::Role",
      "Properties": {
        "Policies": [
          {
            "PolicyDocument": {
              "Statement": {
                "Action": "*",
                "Resource": "*"
              }
            }
          }
        ]
      }
    },
    "InvalidPolicyRole": {
      "Type": "AWS::IAM::Role",
      "Properties": {
        "PolicyDocument": {
          "Statement": ["not an object"]
        }
      }
    },
    "SecurityGroupDict": {
      "Type": "AWS::EC2::SecurityGroup",
      "Properties": {
        "SecurityGroupIngress": {
          "FromPort": 22,
          "ToPort": 22,
          "CidrIp": "0.0.0.0/0"
        }
      }
    },
    "SecurityGroupInvalid": {
      "Type": "AWS::EC2::SecurityGroup",
      "Properties": {
        "SecurityGroupIngress": [
          "not an object",
          {
            "FromPort": "not-a-port",
            "ToPort": 22,
            "CidrIp": "0.0.0.0/0"
          }
        ]
      }
    }
  }
}
""",
            )
        ],
        "uploaded: policy-list.json",
    )

    assert Counter(finding.rule_id for finding in result.findings) == Counter(
        {
            "IAM_WILDCARD_POLICY": 1,
            "OPEN_SSH_INGRESS": 1,
        }
    )


def test_non_json_policy_document_fallback_detects_wildcard_iam_policy() -> None:
    result = scan_files(
        [
            ScanInputFile(
                file_path="inline_policy.yaml",
                content="""
Statement:
  - "Action": "*"
    "Resource": "*"
""",
            )
        ],
        "uploaded: inline_policy.yaml",
    )

    assert Counter(finding.rule_id for finding in result.findings) == Counter({"IAM_WILDCARD_POLICY": 1})
    assert result.findings[0].resource == "IAM policy document"


def test_json_policy_wildcard_check_ignores_non_string_and_non_list_values() -> None:
    result = scan_files(
        [
            ScanInputFile(
                file_path="non-wildcard-policy.json",
                content="""
{
  "Resources": {
    "DynamicPolicy": {
      "Type": "AWS::IAM::Policy",
      "Properties": {
        "PolicyDocument": {
          "Statement": {
            "Action": {"Fn::Join": ["", ["s3:", "*"]]},
            "Resource": "*"
          }
        }
      }
    }
  }
}
""",
            )
        ],
        "uploaded: non-wildcard-policy.json",
    )

    assert result.findings == []


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


def test_secret_rule_ignores_placeholders_variables_and_duplicate_lines() -> None:
    aws_access_key = "AKIA" + ("2" * 16)
    result = scan_files(
        [
            ScanInputFile(
                file_path="secret_edges.tf",
                content=f"""
resource "null_resource" "config" {{
  triggers = {{
    placeholder_password = "todo"
    variable_secret      = var.secret_value
    short_api_token      = "short"
    access_key           = "{aws_access_key}" # admin_password = "duplicate-password"
  }}
}}
""",
            )
        ],
        "uploaded: secret_edges.tf",
    )

    assert Counter(finding.rule_id for finding in result.findings) == Counter({"HARDCODED_SECRET": 1})
    assert (
        result.findings[0].evidence
        == 'access_key           = "AKIA****************" # admin_password = "duplicate-password"'
    )


def test_secret_rule_reports_only_first_aws_key_per_line() -> None:
    first_key = "AKIA" + ("3" * 16)
    second_key = "AKIA" + ("4" * 16)
    result = scan_files(
        [
            ScanInputFile(
                file_path="same_line_keys.tf",
                content=f"""
resource "null_resource" "config" {{
  triggers = {{ first_access_key = "{first_key}" second_access_key = "{second_key}" }}
}}
""",
            )
        ],
        "uploaded: same_line_keys.tf",
    )

    assert Counter(finding.rule_id for finding in result.findings) == Counter({"HARDCODED_SECRET": 1})
    assert first_key not in result.findings[0].evidence
    assert second_key not in result.findings[0].evidence


def test_s3_versioning_and_catalog_rules_ignore_safe_or_duplicate_matches() -> None:
    result = scan_files(
        [
            ScanInputFile(
                file_path="edge_rules.tf",
                content="""
resource "aws_s3_bucket" "versioned" {
  versioning {
    enabled = true
  }
}

resource "aws_ebs_volume" "data" {
  encrypted = false encrypted = false
}
""",
            )
        ],
        "uploaded: edge_rules.tf",
    )

    assert Counter(finding.rule_id for finding in result.findings) == Counter({"AWS_EBS_VOLUME_ENCRYPTED_DISABLED": 1})


def test_risk_score_uses_weighted_density_without_zero_saturation() -> None:
    four_critical_findings = [make_finding("critical", index) for index in range(4)]
    ten_critical_findings = [make_finding("critical", index) for index in range(10)]

    four_critical_score = calculate_risk_score(four_critical_findings, files_scanned=1)
    ten_critical_score = calculate_risk_score(ten_critical_findings, files_scanned=1)
    broader_scope_score = calculate_risk_score(four_critical_findings, files_scanned=20)

    assert calculate_risk_score([], files_scanned=20) == 100
    assert 0 < ten_critical_score < four_critical_score < 100
    assert broader_scope_score > four_critical_score


def test_scanner_helper_edges() -> None:
    empty_json_context = ScanContext(file_path="main.tf", content="", json_resources=None)

    assert list(_iter_json_resources(empty_json_context)) == []
    assert _provider_neutral_resource("CUSTOM", "custom_resource") == "resource"
    assert _provider_neutral_resource("CUSTOM", "third_party_resource") == "third_party_resource"
    assert _line_at("single line", 3) == "single line"
    assert _json_key_line("{}", "Missing") == 1
