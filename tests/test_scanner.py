from pathlib import Path

from app.scanner import calculate_risk_score, scan_path


def test_sample_iac_detects_expected_guardrail_failures() -> None:
    result = scan_path(Path("sample_iac"))

    rule_ids = {finding.rule_id for finding in result.findings}

    assert result.files_scanned == 4
    assert "OPEN_SSH_INGRESS" in rule_ids
    assert "S3_PUBLIC_ACL" in rule_ids
    assert "IAM_WILDCARD_POLICY" in rule_ids
    assert "DATABASE_ENCRYPTION_DISABLED" in rule_ids
    assert result.findings[0].rule_id == "OPEN_SSH_INGRESS"
    assert result.risk_score == 20


def test_risk_score_never_goes_below_zero() -> None:
    result = scan_path(Path("sample_iac"))
    overloaded_findings = result.findings * 10

    assert calculate_risk_score(overloaded_findings) == 0


def test_clean_file_has_full_score(tmp_path: Path) -> None:
    clean_tf = tmp_path / "secure.tf"
    clean_tf.write_text(
        """
resource "aws_security_group" "web" {
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}
""",
        encoding="utf-8",
    )

    result = scan_path(tmp_path)

    assert result.findings == []
    assert result.risk_score == 100
