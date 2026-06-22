import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_scan_passes_when_threshold_is_not_breached() -> None:
    result = run_cli("scan", "sample_iac/scenarios/clean", "--fail-on", "critical")

    assert result.returncode == 0
    assert "Findings: 0" in result.stdout
    assert "PASS: no findings meet or exceed the critical threshold." in result.stdout
    assert result.stderr == ""


def test_cli_scan_fails_when_threshold_is_breached() -> None:
    result = run_cli("scan", "sample_iac", "--fail-on", "critical")

    assert result.returncode == 1
    assert "Findings: 67" in result.stdout
    assert "FAIL: 26 finding(s) meet or exceed the critical threshold." in result.stdout
    assert "CRITICAL OPEN_SSH_INGRESS" in result.stdout
    assert "CRITICAL HARDCODED_SECRET" in result.stdout
    assert result.stderr == ""


def test_cli_scan_reports_missing_paths() -> None:
    result = run_cli("scan", "sample_iac/missing", "--fail-on", "critical")

    assert result.returncode == 2
    assert "Scan target does not exist" in result.stderr
