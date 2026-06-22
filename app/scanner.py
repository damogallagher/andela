import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SUPPORTED_EXTENSIONS = {".tf", ".json", ".template", ".yaml", ".yml"}
SSH_RECOMMENDATION = "Restrict SSH ingress to approved admin CIDR ranges or use a bastion or SSM access pattern."
S3_VERSIONING_RECOMMENDATION = "Enable S3 bucket versioning to improve recovery from accidental overwrite or deletion."
SEVERITY_WEIGHTS = {"critical": 10, "high": 6, "medium": 3, "low": 1}
FILE_SCOPE_WEIGHT = 2
RESOURCE_SCOPE_WEIGHT = 1
RISK_SCORE_DECAY = 4


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


@dataclass(frozen=True)
class ScanContext:
    file_path: str
    content: str
    json_resources: Optional[dict]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    title: str
    severity: str
    description: str
    recommendation: str
    check: Callable[["Rule", ScanContext], list[FindingCandidate]]


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
    risk_score = calculate_risk_score(findings, files_scanned=len(files))
    return ScanResult(
        target_path=target_label,
        files_scanned=len(files),
        risk_score=risk_score,
        findings=findings,
    )


def calculate_risk_score(findings: list[FindingCandidate], files_scanned: int = 1) -> int:
    if not findings:
        return 100

    weighted_risk = sum(SEVERITY_WEIGHTS.get(finding.severity.lower(), SEVERITY_WEIGHTS["low"]) for finding in findings)
    scope_units = max(files_scanned, 1) * FILE_SCOPE_WEIGHT
    scope_units += _affected_resource_count(findings) * RESOURCE_SCOPE_WEIGHT
    numerator = 100 * RISK_SCORE_DECAY * scope_units
    denominator = (RISK_SCORE_DECAY * scope_units) + weighted_risk
    score = (numerator + denominator - 1) // denominator
    return min(score, 99)


def _affected_resource_count(findings: list[FindingCandidate]) -> int:
    affected_resources = {(finding.file_path, finding.resource or finding.rule_id) for finding in findings}
    return len(affected_resources)


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
    context = ScanContext(
        file_path=file_path,
        content=content,
        json_resources=_json_resources(file_path, content),
    )
    findings: list[FindingCandidate] = []
    for rule in RULES:
        findings.extend(rule.check(rule, context))
    return findings


def _json_resources(file_path: str, content: str) -> Optional[dict]:
    if Path(file_path).suffix.lower() not in {".json", ".template"}:
        return None

    try:
        document = json.loads(content)
    except json.JSONDecodeError:
        return None

    resources = document.get("Resources", {}) if isinstance(document, dict) else {}
    return resources if isinstance(resources, dict) else {}


def _iter_json_resources(context: ScanContext):
    if context.json_resources is None:
        return

    for resource_name, resource in context.json_resources.items():
        if not isinstance(resource, dict):
            continue
        resource_type = str(resource.get("Type", "Unknown"))
        properties = resource.get("Properties", {})
        if not isinstance(properties, dict):
            properties = {}
        yield resource_name, resource_type, properties


def _finding(
    rule: Rule,
    context: ScanContext,
    line_number: int,
    resource: str,
    evidence: str,
) -> FindingCandidate:
    return FindingCandidate(
        rule_id=rule.rule_id,
        title=rule.title,
        severity=rule.severity,
        file_path=context.file_path,
        line_number=line_number,
        resource=resource,
        evidence=evidence,
        recommendation=rule.recommendation,
    )


def _public_s3_acl(rule: Rule, context: ScanContext) -> list[FindingCandidate]:
    if context.json_resources is not None:
        findings: list[FindingCandidate] = []
        for resource_name, resource_type, properties in _iter_json_resources(context):
            access_control = str(properties.get("AccessControl", ""))
            if resource_type != "AWS::S3::Bucket" or access_control not in {"PublicRead", "PublicReadWrite"}:
                continue
            findings.append(
                _finding(
                    rule,
                    context,
                    _json_key_line(context.content, "AccessControl"),
                    f"{resource_type}.{resource_name}",
                    f'"AccessControl": "{access_control}"',
                )
            )
        return findings

    findings = []
    for match in re.finditer(r'acl\s*=\s*"public-(?:read|read-write)"', context.content):
        findings.append(
            _finding(
                rule,
                context,
                _line_number(context.content, match.start()),
                _nearest_resource(context.content, match.start()),
                _line_at(context.content, match.start()),
            )
        )
    return findings


def _open_ssh_ingress(rule: Rule, context: ScanContext) -> list[FindingCandidate]:
    if context.json_resources is not None:
        findings: list[FindingCandidate] = []
        for resource_name, resource_type, properties in _iter_json_resources(context):
            if resource_type != "AWS::EC2::SecurityGroup":
                continue

            ingress_rules = properties.get("SecurityGroupIngress", [])
            if isinstance(ingress_rules, dict):
                ingress_rules = [ingress_rules]

            for ingress_rule in ingress_rules:
                if not isinstance(ingress_rule, dict):
                    continue
                exposes_ssh = _safe_int(ingress_rule.get("FromPort"), -1) <= 22 <= _safe_int(
                    ingress_rule.get("ToPort"),
                    -1,
                )
                world_open = ingress_rule.get("CidrIp") == "0.0.0.0/0" or ingress_rule.get("CidrIpv6") == "::/0"
                if exposes_ssh and world_open:
                    findings.append(
                        _finding(
                            rule,
                            context,
                            _json_key_line(context.content, "SecurityGroupIngress"),
                            f"{resource_type}.{resource_name}",
                            _compact(json.dumps(ingress_rule, sort_keys=True)),
                        )
                    )
        return findings

    findings = []
    ingress_blocks = re.finditer(r"ingress\s*\{(?P<body>.*?)\}", context.content, re.DOTALL)
    for block in ingress_blocks:
        body = block.group("body")
        exposes_ssh = re.search(r"from_port\s*=\s*22|to_port\s*=\s*22", body)
        world_open = re.search(r'"0\.0\.0\.0/0"|::/0', body)
        if exposes_ssh and world_open:
            findings.append(
                _finding(
                    rule,
                    context,
                    _line_number(context.content, block.start()),
                    _nearest_resource(context.content, block.start()),
                    _compact(body),
                )
            )
    return findings


def _wildcard_iam_policy(rule: Rule, context: ScanContext) -> list[FindingCandidate]:
    if context.json_resources is not None:
        findings: list[FindingCandidate] = []
        for resource_name, resource_type, properties in _iter_json_resources(context):
            policy_documents = _policy_documents(properties)
            has_wildcard_policy = any(_policy_has_wildcards(policy) for policy in policy_documents)
            if not resource_type.startswith("AWS::IAM::") or not has_wildcard_policy:
                continue
            findings.append(
                _finding(
                    rule,
                    context,
                    _json_key_line(context.content, "PolicyDocument"),
                    f"{resource_type}.{resource_name}",
                    '"Action" and "Resource" both include "*"',
                )
            )
        return findings

    action_wildcard = re.search(r'"Action"\s*:\s*"?\*"?', context.content)
    resource_wildcard = re.search(r'"Resource"\s*:\s*"?\*"?', context.content)
    if not action_wildcard or not resource_wildcard:
        return []
    return [
        _finding(
            rule,
            context,
            _line_number(context.content, action_wildcard.start()),
            "IAM policy document",
            _line_at(context.content, action_wildcard.start()),
        )
    ]


def _unencrypted_database(rule: Rule, context: ScanContext) -> list[FindingCandidate]:
    if context.json_resources is not None:
        findings: list[FindingCandidate] = []
        for resource_name, resource_type, properties in _iter_json_resources(context):
            if resource_type != "AWS::RDS::DBInstance" or properties.get("StorageEncrypted") is not False:
                continue
            findings.append(
                _finding(
                    rule,
                    context,
                    _json_key_line(context.content, "StorageEncrypted"),
                    f"{resource_type}.{resource_name}",
                    '"StorageEncrypted": false',
                )
            )
        return findings

    findings = []
    patterns = [
        r"storage_encrypted\s*=\s*false",
        r'"StorageEncrypted"\s*:\s*false',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, context.content, re.IGNORECASE):
            findings.append(
                _finding(
                    rule,
                    context,
                    _line_number(context.content, match.start()),
                    _nearest_resource(context.content, match.start()),
                    _line_at(context.content, match.start()),
                )
            )
    return findings


def _s3_versioning_disabled(rule: Rule, context: ScanContext) -> list[FindingCandidate]:
    if context.json_resources is not None:
        findings: list[FindingCandidate] = []
        for resource_name, resource_type, properties in _iter_json_resources(context):
            versioning = properties.get("VersioningConfiguration", {})
            if not isinstance(versioning, dict):
                continue
            status = str(versioning.get("Status", ""))
            if resource_type != "AWS::S3::Bucket" or status not in {"Disabled", "Suspended"}:
                continue
            findings.append(
                _finding(
                    rule,
                    context,
                    _json_key_line(context.content, "VersioningConfiguration"),
                    f"{resource_type}.{resource_name}",
                    f'"VersioningConfiguration": "{status}"',
                )
            )
        return findings

    findings = []
    checks = [
        re.finditer(r"versioning\s*\{(?P<body>.*?)\}", context.content, re.DOTALL),
        re.finditer(r"resource\s+\"aws_s3_bucket_versioning\"[^{}]+\{(?P<body>.*?)\n\}", context.content, re.DOTALL),
    ]
    for matches in checks:
        for match in matches:
            body = match.group("body")
            disabled = re.search(r"enabled\s*=\s*false|status\s*=\s*\"Suspended\"", body)
            if not disabled:
                continue
            findings.append(
                _finding(
                    rule,
                    context,
                    _line_number(context.content, match.start()),
                    _nearest_resource(context.content, match.start() + disabled.start()),
                    _compact(body),
                )
            )
    return findings


RULES = (
    Rule(
        rule_id="OPEN_SSH_INGRESS",
        title="SSH exposed to the public internet",
        severity="critical",
        description="Detects security group ingress that exposes SSH to 0.0.0.0/0 or ::/0.",
        recommendation=SSH_RECOMMENDATION,
        check=_open_ssh_ingress,
    ),
    Rule(
        rule_id="S3_PUBLIC_ACL",
        title="Public S3 ACL detected",
        severity="high",
        description="Detects S3 ACL settings that make buckets publicly readable or writable.",
        recommendation="Use private ACLs and enforce public access blocks for S3 buckets.",
        check=_public_s3_acl,
    ),
    Rule(
        rule_id="IAM_WILDCARD_POLICY",
        title="Wildcard IAM policy detected",
        severity="high",
        description="Detects wildcard IAM action and resource policies.",
        recommendation="Replace wildcard actions and resources with least-privilege permissions.",
        check=_wildcard_iam_policy,
    ),
    Rule(
        rule_id="DATABASE_ENCRYPTION_DISABLED",
        title="Database encryption disabled",
        severity="medium",
        description="Detects database resources with storage encryption disabled.",
        recommendation="Enable storage encryption for database resources before deployment.",
        check=_unencrypted_database,
    ),
    Rule(
        rule_id="S3_VERSIONING_DISABLED",
        title="S3 versioning disabled",
        severity="low",
        description="Detects S3 buckets with versioning explicitly disabled or suspended.",
        recommendation=S3_VERSIONING_RECOMMENDATION,
        check=_s3_versioning_disabled,
    ),
)
RULES_BY_ID = {rule.rule_id: rule for rule in RULES}


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


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
