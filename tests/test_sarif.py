from datetime import datetime

from app.config import settings
from app.models import Finding, ScanRun
from app.sarif import build_sarif


def make_scan(target_path: str) -> ScanRun:
    scan = ScanRun(
        id=42,
        label="SARIF path scan",
        target_path=target_path,
        risk_score=80,
        files_scanned=1,
        findings_count=1,
        created_at=datetime(2026, 6, 23, 1, 0, 0),
    )
    scan.findings = [
        Finding(
            id=99,
            scan_run_id=42,
            rule_id="CUSTOM_RULE",
            title="Custom unknown rule",
            severity="informational",
            file_path="nested/main.tf",
            line_number=0,
            resource="custom.resource",
            evidence="custom evidence",
            recommendation="Review custom rule.",
        )
    ]
    return scan


def result_uri(scan: ScanRun) -> str:
    return build_sarif(scan)["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]


def test_sarif_uses_relative_uri_for_absolute_directory_target(monkeypatch, tmp_path) -> None:
    scan_root = tmp_path / "workspace"
    scan_dir = scan_root / "sample_iac"
    scan_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "app_scan_root", scan_root)

    assert result_uri(make_scan(str(scan_dir))) == "sample_iac/nested/main.tf"


def test_sarif_uses_relative_uri_for_absolute_file_target(monkeypatch, tmp_path) -> None:
    scan_root = tmp_path / "workspace"
    scan_file = scan_root / "sample_iac" / "main.tf"
    scan_file.parent.mkdir(parents=True)
    scan_file.write_text('resource "null_resource" "x" {}\n', encoding="utf-8")
    monkeypatch.setattr(settings, "app_scan_root", scan_root)

    assert result_uri(make_scan(str(scan_file))) == "sample_iac/main.tf"


def test_sarif_falls_back_to_finding_path_for_out_of_root_absolute_target(monkeypatch, tmp_path) -> None:
    scan_root = tmp_path / "workspace"
    scan_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr(settings, "app_scan_root", scan_root)

    sarif = build_sarif(make_scan(str(outside)))
    rule = sarif["runs"][0]["tool"]["driver"]["rules"][0]
    result = sarif["runs"][0]["results"][0]

    assert result["level"] == "warning"
    assert rule["name"] == "Custom unknown rule"
    assert rule["properties"]["security-severity"] == "5.0"
    assert result_uri(make_scan(str(outside))) == "nested/main.tf"
    assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 1


def test_sarif_uses_finding_path_for_relative_target() -> None:
    assert result_uri(make_scan("uploaded: nested/main.tf")) == "nested/main.tf"
