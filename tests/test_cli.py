import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest

from app import cli
from app.scanner import scan_path

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


def test_cli_main_reports_missing_paths_in_process() -> None:
    assert cli.main(["scan", "sample_iac/missing", "--fail-on", "critical"]) == 2


def test_cli_main_supports_scan_without_threshold() -> None:
    exit_code = cli.main(["scan", "sample_iac/scenarios/clean", "--max-findings", "0"])

    assert exit_code == 0


def test_cli_main_limits_printed_findings() -> None:
    exit_code = cli.main(["scan", "sample_iac", "--fail-on", "low", "--max-findings", "1"])

    assert exit_code == 1


def test_cli_prints_summary_and_limited_findings_to_streams() -> None:
    result = scan_path(PROJECT_ROOT / "sample_iac")
    threshold_findings = cli._threshold_findings(result.findings, "low")
    summary_stream = StringIO()
    findings_stream = StringIO()

    cli._print_summary(result, "low", threshold_findings, stream=summary_stream)
    cli._print_findings(result.findings, 1, stream=findings_stream)

    assert "Findings: 67" in summary_stream.getvalue()
    assert "FAIL: 67 finding(s) meet or exceed the low threshold." in summary_stream.getvalue()
    assert "CRITICAL OPEN_SSH_INGRESS" in findings_stream.getvalue()
    assert "... 66 more finding(s) not shown." in findings_stream.getvalue()


def test_cli_prints_no_threshold_summary_to_stream() -> None:
    result = scan_path(PROJECT_ROOT / "sample_iac/scenarios/clean")
    summary_stream = StringIO()

    cli._print_summary(result, None, [], stream=summary_stream)

    assert "Findings: 0" in summary_stream.getvalue()
    assert "No fail threshold configured." in summary_stream.getvalue()


def test_cli_prints_passing_threshold_summary_to_stream() -> None:
    result = scan_path(PROJECT_ROOT / "sample_iac/scenarios/clean")
    summary_stream = StringIO()

    cli._print_summary(result, "critical", [], stream=summary_stream)

    assert "PASS: no findings meet or exceed the critical threshold." in summary_stream.getvalue()


def test_cli_main_handles_unknown_command(monkeypatch: pytest.MonkeyPatch) -> None:
    class UnknownParser:
        def parse_args(self, _: object) -> object:
            return type("Args", (), {"command": "unknown"})()

    monkeypatch.setattr(cli, "_parser", lambda: UnknownParser())

    assert cli.main(["unknown"]) == 2


def test_cli_module_entrypoint_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["python -m app.cli", "scan", "sample_iac/scenarios/clean"])

    with pytest.raises(SystemExit) as exc:
        __import__("runpy").run_module("app.cli", run_name="__main__")

    assert exc.value.code == 0
