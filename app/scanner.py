from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Optional


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


@dataclass(frozen=True)
class ScanInputFile:
    file_path: str
    content: str


def scan_path(path: Path) -> ScanResult:
    target = path.resolve()
    if not target.exists():
        raise FileNotFoundError(f"Scan target does not exist: {target}")

    files = [
        ScanInputFile(
            file_path=str(file_path.relative_to(target if target.is_dir() else target.parent)),
            content=file_path.read_text(encoding="utf-8", errors="ignore"),
        )
        for file_path in _collect_files(target)
    ]
    return scan_files(files, str(target))


def scan_files(files: list[ScanInputFile], target_label: str) -> ScanResult:
    findings: list[FindingCandidate] = []
    for scan_file in files:
        findings.extend(_scan_file(scan_file.file_path, scan_file.content))

    findings = sorted(findings, key=lambda finding: (severity_rank(finding.severity), finding.file_path))
    risk_score = calculate_risk_score(findings)
    return ScanResult(
        target_path=target_label,
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
    if Path(file_path).suffix.lower() in {".json", ".template"}:
        parsed_findings = _scan_json_file(file_path, content)
        if parsed_findings is not None:
            return parsed_findings

    checks = [
        _public_s3_acl,
        _open_ssh_ingress,
        _wildcard_iam_policy,
        _unencrypted_database,
        _s3_versioning_disabled,
    ]
    findings: list[FindingCandidate] = []
    for check in checks:
        findings.extend(check(file_path, content))
    return findings


def _scan_json_file(file_path: str, content: str) -> Optional[list[FindingCandidate]]:
    try:
        document = json.loads(content)
    except json.JSONDecodeError:
        return None

    findings: list[FindingCandidate] = []
    resources = document.get("Resources", {}) if isinstance(document, dict) else {}
    if not isinstance(resources, dict):
        return findings

    for resource_name, resource in resources.items():
        if not isinstance(resource, dict):
            continue
        resource_type = str(resource.get("Type", "Unknown"))
        properties = resource.get("Properties", {})
        if not isinstance(properties, dict):
            properties = {}

        findings.extend(_json_public_s3_acl(file_path, content, resource_name, resource_type, properties))
        findings.extend(_json_open_ssh_ingress(file_path, content, resource_name, resource_type, properties))
        findings.extend(_json_unencrypted_database(file_path, content, resource_name, resource_type, properties))
        findings.extend(_json_wildcard_iam_policy(file_path, content, resource_name, resource_type, properties))
        findings.extend(_json_s3_versioning_disabled(file_path, content, resource_name, resource_type, properties))

    return findings


def _json_public_s3_acl(
    file_path: str,
    content: str,
    resource_name: str,
    resource_type: str,
    properties: dict,
) -> list[FindingCandidate]:
    access_control = str(properties.get("AccessControl", ""))
    if resource_type != "AWS::S3::Bucket" or access_control not in {"PublicRead", "PublicReadWrite"}:
        return []
    return [
        FindingCandidate(
            rule_id="S3_PUBLIC_ACL",
            title="Public S3 ACL detected",
            severity="high",
            file_path=file_path,
            line_number=_json_key_line(content, "AccessControl"),
            resource=f"{resource_type}.{resource_name}",
            evidence=f'"AccessControl": "{access_control}"',
            recommendation="Use private ACLs and enforce public access blocks for S3 buckets.",
        )
    ]


def _json_open_ssh_ingress(
    file_path: str,
    content: str,
    resource_name: str,
    resource_type: str,
    properties: dict,
) -> list[FindingCandidate]:
    if resource_type != "AWS::EC2::SecurityGroup":
        return []

    ingress_rules = properties.get("SecurityGroupIngress", [])
    if isinstance(ingress_rules, dict):
        ingress_rules = [ingress_rules]

    findings: list[FindingCandidate] = []
    for ingress_rule in ingress_rules:
        if not isinstance(ingress_rule, dict):
            continue
        exposes_ssh = int(ingress_rule.get("FromPort", -1)) <= 22 <= int(ingress_rule.get("ToPort", -1))
        world_open = ingress_rule.get("CidrIp") == "0.0.0.0/0" or ingress_rule.get("CidrIpv6") == "::/0"
        if exposes_ssh and world_open:
            findings.append(
                FindingCandidate(
                    rule_id="OPEN_SSH_INGRESS",
                    title="SSH exposed to the public internet",
                    severity="critical",
                    file_path=file_path,
                    line_number=_json_key_line(content, "SecurityGroupIngress"),
                    resource=f"{resource_type}.{resource_name}",
                    evidence=_compact(json.dumps(ingress_rule, sort_keys=True)),
                    recommendation="Restrict SSH ingress to approved admin CIDR ranges or use a bastion or SSM access pattern.",
                )
            )
    return findings


def _json_unencrypted_database(
    file_path: str,
    content: str,
    resource_name: str,
    resource_type: str,
    properties: dict,
) -> list[FindingCandidate]:
    if resource_type != "AWS::RDS::DBInstance" or properties.get("StorageEncrypted") is not False:
        return []
    return [
        FindingCandidate(
            rule_id="DATABASE_ENCRYPTION_DISABLED",
            title="Database encryption disabled",
            severity="medium",
            file_path=file_path,
            line_number=_json_key_line(content, "StorageEncrypted"),
            resource=f"{resource_type}.{resource_name}",
            evidence='"StorageEncrypted": false',
            recommendation="Enable storage encryption for database resources before deployment.",
        )
    ]


def _json_wildcard_iam_policy(
    file_path: str,
    content: str,
    resource_name: str,
    resource_type: str,
    properties: dict,
) -> list[FindingCandidate]:
    policy_documents = _policy_documents(properties)
    if not resource_type.startswith("AWS::IAM::") or not any(_policy_has_wildcards(policy) for policy in policy_documents):
        return []
    return [
        FindingCandidate(
            rule_id="IAM_WILDCARD_POLICY",
            title="Wildcard IAM policy detected",
            severity="high",
            file_path=file_path,
            line_number=_json_key_line(content, "PolicyDocument"),
            resource=f"{resource_type}.{resource_name}",
            evidence='"Action" and "Resource" both include "*"',
            recommendation="Replace wildcard actions and resources with least-privilege permissions.",
        )
    ]


def _json_s3_versioning_disabled(
    file_path: str,
    content: str,
    resource_name: str,
    resource_type: str,
    properties: dict,
) -> list[FindingCandidate]:
    versioning = properties.get("VersioningConfiguration", {})
    if not isinstance(versioning, dict):
        return []
    status = str(versioning.get("Status", ""))
    if resource_type != "AWS::S3::Bucket" or status not in {"Disabled", "Suspended"}:
        return []
    return [
        FindingCandidate(
            rule_id="S3_VERSIONING_DISABLED",
            title="S3 versioning disabled",
            severity="low",
            file_path=file_path,
            line_number=_json_key_line(content, "VersioningConfiguration"),
            resource=f"{resource_type}.{resource_name}",
            evidence=f'"VersioningConfiguration": "{status}"',
            recommendation="Enable S3 bucket versioning to improve recovery from accidental overwrite or deletion.",
        )
    ]


def _policy_documents(properties: dict) -> list[dict]:
    documents: list[dict] = []
    direct = properties.get("PolicyDocument")
    if isinstance(direct, dict):
        documents.append(direct)

    for policy in properties.get("Policies", []):
        if isinstance(policy, dict) and isinstance(policy.get("PolicyDocument"), dict):
            documents.append(policy["PolicyDocument"])
    return documents


def _policy_has_wildcards(policy_document: dict) -> bool:
    statements = policy_document.get("Statement", [])
    if isinstance(statements, dict):
        statements = [statements]
    for statement in statements:
        if not isinstance(statement, dict):
            continue
        if _has_wildcard(statement.get("Action")) and _has_wildcard(statement.get("Resource")):
            return True
    return False


def _has_wildcard(value) -> bool:
    if value == "*":
        return True
    if isinstance(value, list):
        return "*" in value
    return False


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


def _s3_versioning_disabled(file_path: str, content: str) -> list[FindingCandidate]:
    findings: list[FindingCandidate] = []
    checks = [
        re.finditer(r"versioning\s*\{(?P<body>.*?)\}", content, re.DOTALL),
        re.finditer(r"resource\s+\"aws_s3_bucket_versioning\"[^{}]+\{(?P<body>.*?)\n\}", content, re.DOTALL),
    ]
    for matches in checks:
        for match in matches:
            body = match.group("body")
            disabled = re.search(r"enabled\s*=\s*false|status\s*=\s*\"Suspended\"", body)
            if not disabled:
                continue
            findings.append(
                FindingCandidate(
                    rule_id="S3_VERSIONING_DISABLED",
                    title="S3 versioning disabled",
                    severity="low",
                    file_path=file_path,
                    line_number=_line_number(content, match.start()),
                    resource=_nearest_resource(content, match.start() + disabled.start()),
                    evidence=_compact(body),
                    recommendation="Enable S3 bucket versioning to improve recovery from accidental overwrite or deletion.",
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


def _json_key_line(content: str, key: str) -> int:
    match = re.search(rf'"{re.escape(key)}"\s*:', content)
    if not match:
        return 1
    return _line_number(content, match.start())


def _nearest_resource(content: str, index: int) -> str:
    prefix = content[:index]
    matches = list(re.finditer(r'resource\s+"([^"]+)"\s+"([^"]+)"', prefix))
    if not matches:
        return "Unknown resource"
    last = matches[-1]
    return f"{last.group(1)}.{last.group(2)}"


def _compact(value: str) -> str:
    return " ".join(value.strip().split())
