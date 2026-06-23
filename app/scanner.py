import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SUPPORTED_EXTENSIONS = {".tf", ".json", ".template", ".yaml", ".yml"}
SSH_RECOMMENDATION = "Restrict SSH ingress to approved admin CIDR ranges or use a bastion or SSM access pattern."
S3_VERSIONING_RECOMMENDATION = "Enable S3 bucket versioning to improve recovery from accidental overwrite or deletion."
SECRET_RECOMMENDATION = (
    "Remove the hardcoded credential, rotate the exposed value, and load it from a secrets manager or CI secret."
)
SEVERITY_WEIGHTS = {"critical": 10, "high": 6, "medium": 3, "low": 1}
FILE_SCOPE_WEIGHT = 2
RESOURCE_SCOPE_WEIGHT = 1
RISK_SCORE_DECAY = 4
AWS_ACCESS_KEY_PATTERN = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?im)(?P<key_quote>[\"']?)(?P<key>[A-Za-z0-9_.:-]*"
    r"(?:password|passwd|secret|api[_-]?key|access[_-]?key|token|client[_-]?secret|private[_-]?key)"
    r"[A-Za-z0-9_.:-]*)(?P=key_quote)\s*[:=]\s*"
    r"(?P<value>\"[^\"\n]*\"|'[^'\n]*'|[^\s,#}\]]+)"
)
NON_LITERAL_SECRET_PREFIXES = ("${", "var.", "local.", "module.", "data.", "file(", "jsonencode(", "sensitive(")
PLACEHOLDER_SECRET_VALUES = {
    "",
    "changeme",
    "change-me",
    "password",
    "replace-me",
    "replace_me",
    "todo",
    "tbd",
    "null",
    "none",
    "true",
    "false",
}


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


@dataclass(frozen=True)
class PatternRuleSpec:
    rule_id: str
    title: str
    severity: str
    description: str
    recommendation: str
    resource_type: str
    line_pattern: str


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
    return sorted(path for path in target.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS)


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


def _hardcoded_secret(rule: Rule, context: ScanContext) -> list[FindingCandidate]:
    findings: list[FindingCandidate] = []
    finding_lines: set[int] = set()

    for match in AWS_ACCESS_KEY_PATTERN.finditer(context.content):
        line_number = _line_number(context.content, match.start())
        if line_number in finding_lines:
            continue
        finding_lines.add(line_number)
        findings.append(
            _finding(
                rule,
                context,
                line_number,
                _nearest_context_resource(context, match.start()),
                _redact_secret_line(_line_at(context.content, match.start())),
            )
        )

    for match in SECRET_ASSIGNMENT_PATTERN.finditer(context.content):
        line_number = _line_number(context.content, match.start())
        if line_number in finding_lines:
            continue

        key = match.group("key")
        value = _secret_value(match.group("value"))
        if not _is_hardcoded_secret_value(key, value):
            continue

        finding_lines.add(line_number)
        findings.append(
            _finding(
                rule,
                context,
                line_number,
                _nearest_context_resource(context, match.start()),
                f"{key} = <redacted>",
            )
        )

    return findings


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
                from_port = _safe_int(ingress_rule.get("FromPort"), 65535)
                to_port = _safe_int(ingress_rule.get("ToPort"), -1)
                exposes_ssh = from_port <= 22 <= to_port
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


def _catalog_pattern_check(rule: Rule, context: ScanContext) -> list[FindingCandidate]:
    spec = CATALOG_PATTERN_SPECS_BY_ID[rule.rule_id]
    findings: list[FindingCandidate] = []
    seen: set[tuple[int, str]] = set()

    for match in re.finditer(spec.line_pattern, context.content, re.IGNORECASE):
        resource = _nearest_resource(context.content, match.start())
        if not resource.startswith(f"{spec.resource_type}."):
            continue

        line_number = _line_number(context.content, match.start())
        finding_key = (line_number, resource)
        if finding_key in seen:
            continue
        seen.add(finding_key)
        findings.append(
            _finding(
                rule,
                context,
                line_number,
                resource,
                _line_at(context.content, match.start()),
            )
        )

    return findings


def _signature_spec(
    provider: str,
    resource_type: str,
    attribute: str,
    bad_value_pattern: str,
    bad_label: str,
    severity: str,
    category: str,
    title: Optional[str] = None,
) -> PatternRuleSpec:
    normalized_resource = _provider_neutral_resource(provider, resource_type)
    return PatternRuleSpec(
        rule_id=_signature_rule_id(provider, resource_type, attribute, bad_label),
        title=title
        or f"{provider} {_humanize_resource(normalized_resource)} {_humanize_attribute(attribute)} {bad_label}",
        severity=severity,
        description=(
            f"Detects {provider} Terraform resources of type {resource_type} where "
            f"{attribute} is set to an insecure value."
        ),
        recommendation=CATALOG_RECOMMENDATIONS[category],
        resource_type=resource_type,
        line_pattern=rf"\b{re.escape(attribute)}\s*=\s*{bad_value_pattern}",
    )


def _signature_rule_id(provider: str, resource_type: str, attribute: str, bad_label: str) -> str:
    normalized_resource = _provider_neutral_resource(provider, resource_type)
    return re.sub(r"[^A-Z0-9]+", "_", f"{provider}_{normalized_resource}_{attribute}_{bad_label}".upper()).strip("_")


def _provider_neutral_resource(provider: str, resource_type: str) -> str:
    normalized_provider = provider.lower()
    if resource_type.startswith(f"{normalized_provider}_"):
        return resource_type.removeprefix(f"{normalized_provider}_")
    if normalized_provider == "azure" and resource_type.startswith("azurerm_"):
        return resource_type.removeprefix("azurerm_")
    return resource_type


def _humanize_resource(resource_type: str) -> str:
    return resource_type.replace("_", " ")


def _humanize_attribute(attribute: str) -> str:
    return attribute.replace("_", " ")


CATALOG_RECOMMENDATIONS = {
    "auth": "Disable local or shared-key authentication paths and use managed identity or IAM roles.",
    "backup": "Enable backups, point-in-time recovery, and retention settings that meet recovery requirements.",
    "deletion": "Enable deletion protection or equivalent safeguards for stateful and critical resources.",
    "encryption": "Enable encryption at rest and in transit using provider-managed or customer-managed keys.",
    "headers": "Enable strict protocol and header handling for internet-facing services.",
    "iam": "Harden IAM and identity policy settings to enforce least privilege and strong authentication.",
    "logging": "Enable audit logging, metrics, tracing, and retention for investigation and compliance.",
    "network": "Disable public exposure and require private endpoints, trusted networks, or explicit allowlists.",
    "runtime": "Disable privileged runtime features and enforce hardened workload defaults.",
    "tls": "Require HTTPS and TLS 1.2 or later for all service endpoints.",
}

TLS_WEAK_VALUE = r'"(?:TLS1_0|TLS1_1|TLSv1|TLSv1\.1|1\.0|1\.1)"'
ZERO_OR_LOW_RETENTION = r"(?:0|[1-9]|[12][0-9])\b"
SHORT_PASSWORD_LENGTH = r"[0-7]\b"

AWS_SIGNATURES = (
    _signature_spec("AWS", "aws_cloudtrail", "enable_logging", "false\\b", "disabled", "high", "logging"),
    _signature_spec(
        "AWS", "aws_cloudtrail", "include_global_service_events", "false\\b", "disabled", "medium", "logging"
    ),
    _signature_spec("AWS", "aws_cloudtrail", "is_multi_region_trail", "false\\b", "disabled", "medium", "logging"),
    _signature_spec("AWS", "aws_cloudtrail", "enable_log_file_validation", "false\\b", "disabled", "medium", "logging"),
    _signature_spec("AWS", "aws_ebs_volume", "encrypted", "false\\b", "disabled", "high", "encryption"),
    _signature_spec("AWS", "aws_efs_file_system", "encrypted", "false\\b", "disabled", "high", "encryption"),
    _signature_spec("AWS", "aws_redshift_cluster", "encrypted", "false\\b", "disabled", "high", "encryption"),
    _signature_spec("AWS", "aws_redshift_cluster", "publicly_accessible", "true\\b", "enabled", "critical", "network"),
    _signature_spec("AWS", "aws_redshift_cluster", "enhanced_vpc_routing", "false\\b", "disabled", "medium", "network"),
    _signature_spec("AWS", "aws_opensearch_domain", "enforce_https", "false\\b", "disabled", "high", "tls"),
    _signature_spec("AWS", "aws_elasticsearch_domain", "enforce_https", "false\\b", "disabled", "high", "tls"),
    _signature_spec("AWS", "aws_neptune_cluster", "storage_encrypted", "false\\b", "disabled", "high", "encryption"),
    _signature_spec("AWS", "aws_neptune_cluster", "deletion_protection", "false\\b", "disabled", "medium", "deletion"),
    _signature_spec(
        "AWS",
        "aws_neptune_cluster",
        "iam_database_authentication_enabled",
        "false\\b",
        "disabled",
        "medium",
        "iam",
    ),
    _signature_spec("AWS", "aws_docdb_cluster", "storage_encrypted", "false\\b", "disabled", "high", "encryption"),
    _signature_spec("AWS", "aws_docdb_cluster", "deletion_protection", "false\\b", "disabled", "medium", "deletion"),
    _signature_spec("AWS", "aws_rds_cluster", "storage_encrypted", "false\\b", "disabled", "high", "encryption"),
    _signature_spec("AWS", "aws_rds_cluster", "deletion_protection", "false\\b", "disabled", "medium", "deletion"),
    _signature_spec("AWS", "aws_rds_cluster", "copy_tags_to_snapshot", "false\\b", "disabled", "low", "backup"),
    _signature_spec(
        "AWS",
        "aws_rds_cluster",
        "iam_database_authentication_enabled",
        "false\\b",
        "disabled",
        "medium",
        "iam",
    ),
    _signature_spec("AWS", "aws_db_instance", "publicly_accessible", "true\\b", "enabled", "critical", "network"),
    _signature_spec("AWS", "aws_db_instance", "deletion_protection", "false\\b", "disabled", "medium", "deletion"),
    _signature_spec("AWS", "aws_db_instance", "backup_retention_period", "0\\b", "zero", "medium", "backup"),
    _signature_spec("AWS", "aws_db_instance", "skip_final_snapshot", "true\\b", "enabled", "low", "backup"),
    _signature_spec("AWS", "aws_db_instance", "copy_tags_to_snapshot", "false\\b", "disabled", "low", "backup"),
    _signature_spec(
        "AWS",
        "aws_db_instance",
        "iam_database_authentication_enabled",
        "false\\b",
        "disabled",
        "medium",
        "iam",
    ),
    _signature_spec("AWS", "aws_db_instance", "performance_insights_enabled", "false\\b", "disabled", "low", "logging"),
    _signature_spec("AWS", "aws_db_instance", "monitoring_interval", "0\\b", "zero", "low", "logging"),
    _signature_spec(
        "AWS", "aws_s3_bucket_public_access_block", "block_public_acls", "false\\b", "disabled", "high", "network"
    ),
    _signature_spec(
        "AWS", "aws_s3_bucket_public_access_block", "block_public_policy", "false\\b", "disabled", "high", "network"
    ),
    _signature_spec(
        "AWS", "aws_s3_bucket_public_access_block", "ignore_public_acls", "false\\b", "disabled", "medium", "network"
    ),
    _signature_spec(
        "AWS",
        "aws_s3_bucket_public_access_block",
        "restrict_public_buckets",
        "false\\b",
        "disabled",
        "high",
        "network",
    ),
    _signature_spec(
        "AWS", "aws_s3_account_public_access_block", "block_public_acls", "false\\b", "disabled", "high", "network"
    ),
    _signature_spec(
        "AWS", "aws_s3_account_public_access_block", "block_public_policy", "false\\b", "disabled", "high", "network"
    ),
    _signature_spec(
        "AWS", "aws_s3_account_public_access_block", "ignore_public_acls", "false\\b", "disabled", "medium", "network"
    ),
    _signature_spec(
        "AWS",
        "aws_s3_account_public_access_block",
        "restrict_public_buckets",
        "false\\b",
        "disabled",
        "high",
        "network",
    ),
    _signature_spec(
        "AWS",
        "aws_elasticache_replication_group",
        "at_rest_encryption_enabled",
        "false\\b",
        "disabled",
        "high",
        "encryption",
    ),
    _signature_spec(
        "AWS",
        "aws_elasticache_replication_group",
        "transit_encryption_enabled",
        "false\\b",
        "disabled",
        "high",
        "encryption",
    ),
    _signature_spec(
        "AWS",
        "aws_elasticache_replication_group",
        "automatic_failover_enabled",
        "false\\b",
        "disabled",
        "medium",
        "backup",
    ),
    _signature_spec("AWS", "aws_lb", "enable_deletion_protection", "false\\b", "disabled", "low", "deletion"),
    _signature_spec("AWS", "aws_lb", "drop_invalid_header_fields", "false\\b", "disabled", "medium", "headers"),
    _signature_spec("AWS", "aws_lb", "enable_http2", "false\\b", "disabled", "low", "headers"),
    _signature_spec("AWS", "aws_alb", "enable_deletion_protection", "false\\b", "disabled", "low", "deletion"),
    _signature_spec("AWS", "aws_alb", "drop_invalid_header_fields", "false\\b", "disabled", "medium", "headers"),
    _signature_spec("AWS", "aws_alb", "enable_http2", "false\\b", "disabled", "low", "headers"),
    _signature_spec("AWS", "aws_api_gateway_stage", "xray_tracing_enabled", "false\\b", "disabled", "low", "logging"),
    _signature_spec(
        "AWS", "aws_api_gateway_stage", "cache_data_encrypted", "false\\b", "disabled", "medium", "encryption"
    ),
    _signature_spec("AWS", "aws_lambda_function", "mode", '"PassThrough"', "passthrough", "low", "logging"),
    _signature_spec(
        "AWS", "aws_cloudwatch_log_group", "retention_in_days", ZERO_OR_LOW_RETENTION, "low", "low", "logging"
    ),
    _signature_spec("AWS", "aws_kms_key", "enable_key_rotation", "false\\b", "disabled", "medium", "encryption"),
    _signature_spec("AWS", "aws_kms_key", "deletion_window_in_days", r"(?:7|8|9)\b", "short", "low", "deletion"),
    _signature_spec(
        "AWS",
        "aws_iam_account_password_policy",
        "require_uppercase_characters",
        "false\\b",
        "disabled",
        "medium",
        "iam",
    ),
    _signature_spec(
        "AWS",
        "aws_iam_account_password_policy",
        "require_lowercase_characters",
        "false\\b",
        "disabled",
        "medium",
        "iam",
    ),
    _signature_spec(
        "AWS", "aws_iam_account_password_policy", "require_numbers", "false\\b", "disabled", "medium", "iam"
    ),
    _signature_spec(
        "AWS", "aws_iam_account_password_policy", "require_symbols", "false\\b", "disabled", "medium", "iam"
    ),
    _signature_spec(
        "AWS",
        "aws_iam_account_password_policy",
        "minimum_password_length",
        SHORT_PASSWORD_LENGTH,
        "short",
        "medium",
        "iam",
    ),
    _signature_spec("AWS", "aws_iam_account_password_policy", "max_password_age", "0\\b", "zero", "low", "iam"),
    _signature_spec(
        "AWS",
        "aws_iam_account_password_policy",
        "allow_users_to_change_password",
        "false\\b",
        "disabled",
        "low",
        "iam",
    ),
    _signature_spec("AWS", "aws_ecr_repository", "image_tag_mutability", '"MUTABLE"', "mutable", "medium", "runtime"),
    _signature_spec("AWS", "aws_ecr_repository", "scan_on_push", "false\\b", "disabled", "medium", "runtime"),
    _signature_spec("AWS", "aws_ecs_task_definition", "privileged", "true\\b", "enabled", "critical", "runtime"),
    _signature_spec(
        "AWS", "aws_ecs_task_definition", "readonly_root_filesystem", "false\\b", "disabled", "medium", "runtime"
    ),
    _signature_spec("AWS", "aws_instance", "associate_public_ip_address", "true\\b", "enabled", "high", "network"),
    _signature_spec("AWS", "aws_instance", "monitoring", "false\\b", "disabled", "low", "logging"),
    _signature_spec(
        "AWS", "aws_launch_template", "associate_public_ip_address", "true\\b", "enabled", "high", "network"
    ),
    _signature_spec("AWS", "aws_launch_template", "http_tokens", '"optional"', "optional", "medium", "iam"),
    _signature_spec("AWS", "aws_sqs_queue", "sqs_managed_sse_enabled", "false\\b", "disabled", "medium", "encryption"),
    _signature_spec(
        "AWS", "aws_dynamodb_table", "deletion_protection_enabled", "false\\b", "disabled", "medium", "deletion"
    ),
    _signature_spec(
        "AWS", "aws_dynamodb_table", "point_in_time_recovery_enabled", "false\\b", "disabled", "medium", "backup"
    ),
    _signature_spec("AWS", "aws_mq_broker", "publicly_accessible", "true\\b", "enabled", "critical", "network"),
    _signature_spec("AWS", "aws_transfer_server", "endpoint_type", '"PUBLIC"', "public", "high", "network"),
    _signature_spec(
        "AWS",
        "aws_cloudfront_distribution",
        "viewer_protocol_policy",
        '"allow-all"',
        "allow_all",
        "high",
        "tls",
    ),
    _signature_spec(
        "AWS",
        "aws_cloudfront_distribution",
        "minimum_protocol_version",
        '"TLSv1"',
        "weak_tls",
        "high",
        "tls",
    ),
    _signature_spec(
        "AWS",
        "aws_acm_certificate",
        "certificate_transparency_logging_preference",
        '"DISABLED"',
        "disabled",
        "low",
        "logging",
    ),
    _signature_spec("AWS", "aws_backup_vault", "force_destroy", "true\\b", "enabled", "medium", "deletion"),
)

AZURE_SIGNATURES = (
    _signature_spec(
        "AZURE", "azurerm_storage_account", "enable_https_traffic_only", "false\\b", "disabled", "high", "tls"
    ),
    _signature_spec("AZURE", "azurerm_storage_account", "min_tls_version", TLS_WEAK_VALUE, "weak_tls", "high", "tls"),
    _signature_spec(
        "AZURE", "azurerm_storage_account", "allow_blob_public_access", "true\\b", "enabled", "high", "network"
    ),
    _signature_spec(
        "AZURE", "azurerm_storage_account", "shared_access_key_enabled", "true\\b", "enabled", "medium", "auth"
    ),
    _signature_spec(
        "AZURE", "azurerm_storage_account", "public_network_access_enabled", "true\\b", "enabled", "high", "network"
    ),
    _signature_spec("AZURE", "azurerm_storage_account", "nfsv3_enabled", "true\\b", "enabled", "medium", "network"),
    _signature_spec(
        "AZURE",
        "azurerm_storage_account",
        "cross_tenant_replication_enabled",
        "true\\b",
        "enabled",
        "medium",
        "network",
    ),
    _signature_spec(
        "AZURE",
        "azurerm_storage_account",
        "infrastructure_encryption_enabled",
        "false\\b",
        "disabled",
        "medium",
        "encryption",
    ),
    _signature_spec(
        "AZURE", "azurerm_key_vault", "purge_protection_enabled", "false\\b", "disabled", "medium", "deletion"
    ),
    _signature_spec("AZURE", "azurerm_key_vault", "soft_delete_retention_days", "0\\b", "zero", "medium", "deletion"),
    _signature_spec(
        "AZURE", "azurerm_key_vault", "public_network_access_enabled", "true\\b", "enabled", "high", "network"
    ),
    _signature_spec("AZURE", "azurerm_key_vault", "enabled_for_deployment", "true\\b", "enabled", "low", "iam"),
    _signature_spec(
        "AZURE", "azurerm_key_vault", "enabled_for_template_deployment", "true\\b", "enabled", "low", "iam"
    ),
    _signature_spec(
        "AZURE", "azurerm_key_vault", "enabled_for_disk_encryption", "false\\b", "disabled", "low", "encryption"
    ),
    _signature_spec(
        "AZURE", "azurerm_mssql_server", "public_network_access_enabled", "true\\b", "enabled", "critical", "network"
    ),
    _signature_spec("AZURE", "azurerm_mssql_server", "minimum_tls_version", TLS_WEAK_VALUE, "weak_tls", "high", "tls"),
    _signature_spec(
        "AZURE",
        "azurerm_mssql_server",
        "outbound_network_restriction_enabled",
        "false\\b",
        "disabled",
        "medium",
        "network",
    ),
    _signature_spec(
        "AZURE",
        "azurerm_mssql_database",
        "transparent_data_encryption_enabled",
        "false\\b",
        "disabled",
        "high",
        "encryption",
    ),
    _signature_spec("AZURE", "azurerm_mssql_database", "zone_redundant", "false\\b", "disabled", "low", "backup"),
    _signature_spec(
        "AZURE",
        "azurerm_mysql_flexible_server",
        "public_network_access_enabled",
        "true\\b",
        "enabled",
        "critical",
        "network",
    ),
    _signature_spec(
        "AZURE", "azurerm_mysql_flexible_server", "backup_retention_days", r"[1-6]\b", "low", "medium", "backup"
    ),
    _signature_spec(
        "AZURE",
        "azurerm_postgresql_flexible_server",
        "public_network_access_enabled",
        "true\\b",
        "enabled",
        "critical",
        "network",
    ),
    _signature_spec(
        "AZURE", "azurerm_postgresql_flexible_server", "backup_retention_days", r"[1-6]\b", "low", "medium", "backup"
    ),
    _signature_spec(
        "AZURE", "azurerm_cosmosdb_account", "public_network_access_enabled", "true\\b", "enabled", "high", "network"
    ),
    _signature_spec(
        "AZURE", "azurerm_cosmosdb_account", "local_authentication_disabled", "false\\b", "disabled", "medium", "auth"
    ),
    _signature_spec(
        "AZURE", "azurerm_cosmosdb_account", "automatic_failover_enabled", "false\\b", "disabled", "medium", "backup"
    ),
    _signature_spec(
        "AZURE", "azurerm_kubernetes_cluster", "local_account_disabled", "false\\b", "disabled", "high", "iam"
    ),
    _signature_spec(
        "AZURE", "azurerm_kubernetes_cluster", "private_cluster_enabled", "false\\b", "disabled", "high", "network"
    ),
    _signature_spec(
        "AZURE",
        "azurerm_kubernetes_cluster",
        "role_based_access_control_enabled",
        "false\\b",
        "disabled",
        "critical",
        "iam",
    ),
    _signature_spec(
        "AZURE", "azurerm_kubernetes_cluster", "oidc_issuer_enabled", "false\\b", "disabled", "medium", "iam"
    ),
    _signature_spec(
        "AZURE", "azurerm_kubernetes_cluster", "azure_policy_enabled", "false\\b", "disabled", "medium", "iam"
    ),
    _signature_spec(
        "AZURE",
        "azurerm_kubernetes_cluster",
        "http_application_routing_enabled",
        "true\\b",
        "enabled",
        "medium",
        "network",
    ),
    _signature_spec("AZURE", "azurerm_container_registry", "admin_enabled", "true\\b", "enabled", "high", "auth"),
    _signature_spec(
        "AZURE", "azurerm_container_registry", "public_network_access_enabled", "true\\b", "enabled", "high", "network"
    ),
    _signature_spec(
        "AZURE", "azurerm_container_registry", "quarantine_policy_enabled", "false\\b", "disabled", "low", "runtime"
    ),
    _signature_spec(
        "AZURE", "azurerm_container_registry", "trust_policy_enabled", "false\\b", "disabled", "medium", "runtime"
    ),
    _signature_spec(
        "AZURE",
        "azurerm_linux_virtual_machine",
        "disable_password_authentication",
        "false\\b",
        "disabled",
        "high",
        "iam",
    ),
    _signature_spec(
        "AZURE",
        "azurerm_linux_virtual_machine",
        "encryption_at_host_enabled",
        "false\\b",
        "disabled",
        "medium",
        "encryption",
    ),
    _signature_spec(
        "AZURE",
        "azurerm_windows_virtual_machine",
        "enable_automatic_updates",
        "false\\b",
        "disabled",
        "medium",
        "runtime",
    ),
    _signature_spec(
        "AZURE", "azurerm_windows_virtual_machine", "provision_vm_agent", "false\\b", "disabled", "medium", "runtime"
    ),
    _signature_spec(
        "AZURE",
        "azurerm_windows_virtual_machine",
        "encryption_at_host_enabled",
        "false\\b",
        "disabled",
        "medium",
        "encryption",
    ),
    _signature_spec(
        "AZURE",
        "azurerm_network_security_rule",
        "source_address_prefix",
        r'"(?:\*|0\.0\.0\.0/0)"',
        "public",
        "high",
        "network",
    ),
    _signature_spec(
        "AZURE", "azurerm_network_security_rule", "destination_port_range", '"22"', "ssh", "high", "network"
    ),
    _signature_spec("AZURE", "azurerm_app_service", "https_only", "false\\b", "disabled", "high", "tls"),
    _signature_spec("AZURE", "azurerm_app_service", "client_cert_enabled", "false\\b", "disabled", "medium", "auth"),
    _signature_spec("AZURE", "azurerm_linux_web_app", "https_only", "false\\b", "disabled", "high", "tls"),
    _signature_spec(
        "AZURE", "azurerm_linux_web_app", "public_network_access_enabled", "true\\b", "enabled", "medium", "network"
    ),
    _signature_spec(
        "AZURE", "azurerm_linux_web_app", "client_certificate_enabled", "false\\b", "disabled", "medium", "auth"
    ),
    _signature_spec("AZURE", "azurerm_windows_web_app", "https_only", "false\\b", "disabled", "high", "tls"),
    _signature_spec(
        "AZURE", "azurerm_windows_web_app", "public_network_access_enabled", "true\\b", "enabled", "medium", "network"
    ),
    _signature_spec(
        "AZURE", "azurerm_windows_web_app", "client_certificate_enabled", "false\\b", "disabled", "medium", "auth"
    ),
    _signature_spec("AZURE", "azurerm_function_app", "https_only", "false\\b", "disabled", "high", "tls"),
    _signature_spec("AZURE", "azurerm_function_app", "client_cert_mode", '"Optional"', "optional", "low", "auth"),
    _signature_spec("AZURE", "azurerm_linux_function_app", "https_only", "false\\b", "disabled", "high", "tls"),
    _signature_spec(
        "AZURE",
        "azurerm_linux_function_app",
        "public_network_access_enabled",
        "true\\b",
        "enabled",
        "medium",
        "network",
    ),
    _signature_spec("AZURE", "azurerm_windows_function_app", "https_only", "false\\b", "disabled", "high", "tls"),
    _signature_spec(
        "AZURE",
        "azurerm_windows_function_app",
        "public_network_access_enabled",
        "true\\b",
        "enabled",
        "medium",
        "network",
    ),
    _signature_spec("AZURE", "azurerm_application_gateway", "enable_http2", "false\\b", "disabled", "low", "headers"),
    _signature_spec("AZURE", "azurerm_cdn_endpoint", "is_http_allowed", "true\\b", "enabled", "medium", "tls"),
    _signature_spec("AZURE", "azurerm_cdn_endpoint", "is_https_allowed", "false\\b", "disabled", "medium", "tls"),
    _signature_spec(
        "AZURE", "azurerm_monitor_diagnostic_setting", "enabled", "false\\b", "disabled", "medium", "logging"
    ),
    _signature_spec(
        "AZURE", "azurerm_log_analytics_workspace", "retention_in_days", ZERO_OR_LOW_RETENTION, "low", "low", "logging"
    ),
    _signature_spec(
        "AZURE", "azurerm_managed_disk", "public_network_access_enabled", "true\\b", "enabled", "medium", "network"
    ),
    _signature_spec(
        "AZURE", "azurerm_managed_disk", "encryption_settings_enabled", "false\\b", "disabled", "high", "encryption"
    ),
    _signature_spec("AZURE", "azurerm_redis_cache", "enable_non_ssl_port", "true\\b", "enabled", "high", "tls"),
    _signature_spec("AZURE", "azurerm_redis_cache", "minimum_tls_version", TLS_WEAK_VALUE, "weak_tls", "high", "tls"),
    _signature_spec(
        "AZURE", "azurerm_redis_cache", "public_network_access_enabled", "true\\b", "enabled", "high", "network"
    ),
    _signature_spec(
        "AZURE",
        "azurerm_servicebus_namespace",
        "public_network_access_enabled",
        "true\\b",
        "enabled",
        "medium",
        "network",
    ),
    _signature_spec(
        "AZURE", "azurerm_servicebus_namespace", "local_auth_enabled", "true\\b", "enabled", "medium", "auth"
    ),
    _signature_spec(
        "AZURE", "azurerm_servicebus_namespace", "minimum_tls_version", TLS_WEAK_VALUE, "weak_tls", "medium", "tls"
    ),
    _signature_spec(
        "AZURE",
        "azurerm_eventhub_namespace",
        "public_network_access_enabled",
        "true\\b",
        "enabled",
        "medium",
        "network",
    ),
    _signature_spec(
        "AZURE", "azurerm_eventhub_namespace", "local_authentication_enabled", "true\\b", "enabled", "medium", "auth"
    ),
    _signature_spec(
        "AZURE", "azurerm_eventhub_namespace", "minimum_tls_version", TLS_WEAK_VALUE, "weak_tls", "medium", "tls"
    ),
    _signature_spec(
        "AZURE", "azurerm_synapse_workspace", "public_network_access_enabled", "true\\b", "enabled", "high", "network"
    ),
    _signature_spec(
        "AZURE",
        "azurerm_synapse_workspace",
        "managed_virtual_network_enabled",
        "false\\b",
        "disabled",
        "medium",
        "network",
    ),
    _signature_spec(
        "AZURE",
        "azurerm_synapse_workspace",
        "data_exfiltration_protection_enabled",
        "false\\b",
        "disabled",
        "medium",
        "network",
    ),
    _signature_spec(
        "AZURE",
        "azurerm_machine_learning_workspace",
        "public_network_access_enabled",
        "true\\b",
        "enabled",
        "medium",
        "network",
    ),
    _signature_spec(
        "AZURE", "azurerm_cognitive_account", "public_network_access_enabled", "true\\b", "enabled", "medium", "network"
    ),
    _signature_spec("AZURE", "azurerm_cognitive_account", "local_auth_enabled", "true\\b", "enabled", "medium", "auth"),
)

CATALOG_PATTERN_SPECS = AWS_SIGNATURES + AZURE_SIGNATURES
CATALOG_PATTERN_SPECS_BY_ID = {spec.rule_id: spec for spec in CATALOG_PATTERN_SPECS}


CORE_RULES = (
    Rule(
        rule_id="OPEN_SSH_INGRESS",
        title="SSH exposed to the public internet",
        severity="critical",
        description="Detects security group ingress that exposes SSH to 0.0.0.0/0 or ::/0.",
        recommendation=SSH_RECOMMENDATION,
        check=_open_ssh_ingress,
    ),
    Rule(
        rule_id="HARDCODED_SECRET",
        title="Hardcoded credential detected",
        severity="critical",
        description="Detects AWS access keys and hardcoded password, token, secret, and API key assignments.",
        recommendation=SECRET_RECOMMENDATION,
        check=_hardcoded_secret,
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

CATALOG_RULES = tuple(
    Rule(
        rule_id=spec.rule_id,
        title=spec.title,
        severity=spec.severity,
        description=spec.description,
        recommendation=spec.recommendation,
        check=_catalog_pattern_check,
    )
    for spec in CATALOG_PATTERN_SPECS
)
RULES = CORE_RULES + CATALOG_RULES
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


def _secret_value(raw_value: str) -> str:
    return raw_value.strip().strip("\"'")


def _is_hardcoded_secret_value(key: str, value: str) -> bool:
    normalized = value.strip()
    lowered = normalized.lower()
    if lowered in PLACEHOLDER_SECRET_VALUES:
        return False
    if lowered.startswith(NON_LITERAL_SECRET_PREFIXES):
        return False
    if len(normalized) < _minimum_secret_length(key):
        return False
    return True


def _minimum_secret_length(key: str) -> int:
    key_lower = key.lower()
    if "password" in key_lower or "passwd" in key_lower:
        return 4
    return 8


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


def _nearest_context_resource(context: ScanContext, index: int) -> str:
    if context.json_resources is not None:
        resource = _nearest_json_resource(context, index)
        if resource:
            return resource
    return _nearest_resource(context.content, index)


def _nearest_json_resource(context: ScanContext, index: int) -> Optional[str]:
    nearest: Optional[tuple[int, str]] = None
    for resource_name, resource_type, _ in _iter_json_resources(context):
        match = re.search(rf'"{re.escape(resource_name)}"\s*:', context.content)
        if match and match.start() <= index and (nearest is None or match.start() > nearest[0]):
            nearest = (match.start(), f"{resource_type}.{resource_name}")
    return nearest[1] if nearest else None


def _redact_secret_line(line: str) -> str:
    return AWS_ACCESS_KEY_PATTERN.sub(lambda match: f"{match.group(0)[:4]}****************", line)


def _compact(value: str) -> str:
    return " ".join(value.strip().split())
