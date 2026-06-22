from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from app.scanner import FindingCandidate, ScanResult, scan_path, severity_rank

SEVERITIES = ("critical", "high", "medium", "low")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "scan":
        return _scan(args)
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Andela guardrail auditor command line interface.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan Terraform and JSON infrastructure files.")
    scan_parser.add_argument("path", help="File or directory path to scan.")
    scan_parser.add_argument(
        "--fail-on",
        choices=SEVERITIES,
        help="Exit non-zero when any finding is at or above the selected severity.",
    )
    scan_parser.add_argument(
        "--max-findings",
        type=int,
        default=20,
        help="Maximum number of findings to print in text output. Defaults to 20.",
    )
    return parser


def _scan(args: argparse.Namespace) -> int:
    try:
        result = scan_path(Path(args.path))
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    threshold_findings = _threshold_findings(result.findings, args.fail_on)
    _print_summary(result, args.fail_on, threshold_findings)
    _print_findings(result.findings, args.max_findings)

    if args.fail_on and threshold_findings:
        return 1
    return 0


def _threshold_findings(findings: list[FindingCandidate], threshold: str | None) -> list[FindingCandidate]:
    if not threshold:
        return []
    threshold_rank = severity_rank(threshold)
    return [finding for finding in findings if severity_rank(finding.severity) <= threshold_rank]


def _print_summary(
    result: ScanResult,
    threshold: str | None,
    threshold_findings: list[FindingCandidate],
    stream: TextIO = sys.stdout,
) -> None:
    severity_counts = Counter(finding.severity.lower() for finding in result.findings)
    formatted_counts = " ".join(f"{severity}={severity_counts.get(severity, 0)}" for severity in SEVERITIES)

    print(f"Scanned: {result.target_path}", file=stream)
    print(f"Files scanned: {result.files_scanned}", file=stream)
    print(f"Findings: {len(result.findings)}", file=stream)
    print(f"Risk score: {result.risk_score}", file=stream)
    print(f"Severity counts: {formatted_counts}", file=stream)

    if not threshold:
        print("No fail threshold configured.", file=stream)
        return

    if threshold_findings:
        print(
            f"FAIL: {len(threshold_findings)} finding(s) meet or exceed the {threshold} threshold.",
            file=stream,
        )
    else:
        print(f"PASS: no findings meet or exceed the {threshold} threshold.", file=stream)


def _print_findings(findings: list[FindingCandidate], max_findings: int, stream: TextIO = sys.stdout) -> None:
    if not findings:
        return

    safe_limit = max(max_findings, 0)
    printed_findings = findings[:safe_limit]
    for finding in printed_findings:
        print(
            f"{finding.severity.upper()} {finding.rule_id} {finding.file_path}:{finding.line_number} "
            f"{finding.resource} - {finding.title}",
            file=stream,
        )

    remaining_count = len(findings) - len(printed_findings)
    if remaining_count > 0:
        print(f"... {remaining_count} more finding(s) not shown.", file=stream)


if __name__ == "__main__":
    raise SystemExit(main())
