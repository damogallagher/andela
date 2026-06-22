from dataclasses import dataclass
from pathlib import Path
import re


SUPPORTED_EXTENSIONS = {".tf", ".json", ".template", ".yaml", ".yml"}


@dataclass(frozen=True)
class FindingCandidate:
    rule_id: str
    title: str
    severity: str
    file_path: str
    line_number: int
    resource: str
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class ScanResult:
    target_path: str
    files_scanned: int
    risk_score: int
    findings: list[FindingCandidate]


def scan_path(path: Path) -> ScanResult:
    target = path.resolve()
    if not target.exists():
        raise FileNotFoundError(f"Scan target does not exist: {target}")

    files = _collect_files(target)
    findings: list[FindingCandidate] = []
    for file_path in files:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        relative_path = str(file_path.relative_to(target if target.is_dir() else target.parent))
        findings.extend(_scan_file(relative_path, content))

    findings = sorted(findings, key=lambda finding: (severity_rank(finding.severity), finding.file_path))
    risk_score = calculate_risk_score(findings)
    return ScanResult(
        target_path=str(target),
        files_scanned=len(files),
        risk_score=risk_score,
        findings=findings,
    )


def calculate_risk_score(findings: list[FindingCandidate]) -> int:
    penalties = {"critical": 30, "high": 20, "medium": 10, "low": 5}
    score = 100
    for finding in findings:
        score -= penalties.get(finding.severity.lower(), 5)
    return max(score, 0)


def severity_rank(severity: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(severity.lower(), 4)


def _collect_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() in SUPPORTED_EXTENSIONS else []
    return sorted(
        path
        for path in target.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _scan_file(file_path: str, content: str) -> list[FindingCandidate]:
    checks = [
        _public_s3_acl,
        _open_ssh_ingress,
        _wildcard_iam_policy,
        _unencrypted_database,
    ]
    findings: list[FindingCandidate] = []
    for check in checks:
        findings.extend(check(file_path, content))
    return findings


def _public_s3_acl(file_path: str, content: str) -> list[FindingCandidate]:
    findings: list[FindingCandidate] = []
    for match in re.finditer(r'acl\s*=\s*"public-(?:read|read-write)"', content):
        findings.append(
            FindingCandidate(
                rule_id="S3_PUBLIC_ACL",
                title="Public S3 ACL detected",
                severity="high",
                file_path=file_path,
                line_number=_line_number(content, match.start()),
                resource=_nearest_resource(content, match.start()),
                evidence=_line_at(content, match.start()),
                recommendation="Use private ACLs and enforce public access blocks for S3 buckets.",
            )
        )
    return findings


def _open_ssh_ingress(file_path: str, content: str) -> list[FindingCandidate]:
    findings: list[FindingCandidate] = []
    ingress_blocks = re.finditer(r"ingress\s*\{(?P<body>.*?)\}", content, re.DOTALL)
    for block in ingress_blocks:
        body = block.group("body")
        exposes_ssh = re.search(r"from_port\s*=\s*22|to_port\s*=\s*22", body)
        world_open = re.search(r'"0\.0\.0\.0/0"|::/0', body)
        if exposes_ssh and world_open:
            findings.append(
                FindingCandidate(
                    rule_id="OPEN_SSH_INGRESS",
                    title="SSH exposed to the public internet",
                    severity="critical",
                    file_path=file_path,
                    line_number=_line_number(content, block.start()),
                    resource=_nearest_resource(content, block.start()),
                    evidence=_compact(body),
                    recommendation="Restrict SSH ingress to approved admin CIDR ranges or use a bastion or SSM access pattern.",
                )
            )
    return findings


def _wildcard_iam_policy(file_path: str, content: str) -> list[FindingCandidate]:
    action_wildcard = re.search(r'"Action"\s*:\s*"?\*"?', content)
    resource_wildcard = re.search(r'"Resource"\s*:\s*"?\*"?', content)
    if not action_wildcard or not resource_wildcard:
        return []
    return [
        FindingCandidate(
            rule_id="IAM_WILDCARD_POLICY",
            title="Wildcard IAM policy detected",
            severity="high",
            file_path=file_path,
            line_number=_line_number(content, action_wildcard.start()),
            resource="IAM policy document",
            evidence=_line_at(content, action_wildcard.start()),
            recommendation="Replace wildcard actions and resources with least-privilege permissions.",
        )
    ]


def _unencrypted_database(file_path: str, content: str) -> list[FindingCandidate]:
    findings: list[FindingCandidate] = []
    patterns = [
        r"storage_encrypted\s*=\s*false",
        r'"StorageEncrypted"\s*:\s*false',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            findings.append(
                FindingCandidate(
                    rule_id="DATABASE_ENCRYPTION_DISABLED",
                    title="Database encryption disabled",
                    severity="medium",
                    file_path=file_path,
                    line_number=_line_number(content, match.start()),
                    resource=_nearest_resource(content, match.start()),
                    evidence=_line_at(content, match.start()),
                    recommendation="Enable storage encryption for database resources before deployment.",
                )
            )
    return findings


def _line_number(content: str, index: int) -> int:
    return content.count("\n", 0, index) + 1


def _line_at(content: str, index: int) -> str:
    line_start = content.rfind("\n", 0, index) + 1
    line_end = content.find("\n", index)
    if line_end == -1:
        line_end = len(content)
    return content[line_start:line_end].strip()


def _nearest_resource(content: str, index: int) -> str:
    prefix = content[:index]
    matches = list(re.finditer(r'resource\s+"([^"]+)"\s+"([^"]+)"', prefix))
    if not matches:
        return "Unknown resource"
    last = matches[-1]
    return f"{last.group(1)}.{last.group(2)}"


def _compact(value: str) -> str:
    return " ".join(value.strip().split())
