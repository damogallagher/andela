import { expect } from "@playwright/test";

const createdAt = "2026-06-22T22:35:00";

function makeFinding(id, severity, index, overrides = {}) {
  const catalog = {
    critical: {
      rule_id: "OPEN_SSH_INGRESS",
      title: "SSH exposed to the public internet",
      resource: `AWS::EC2::SecurityGroup.SyntheticOpenSshSecurityGroup${String(index).padStart(2, "0")}`,
      file_path: "sample_iac/scenarios/large_violations/synthetic_large_violations.json",
      recommendation: "Restrict SSH ingress to approved admin CIDR ranges or use a bastion or SSM access pattern.",
      evidence: "{\"CidrIp\":\"0.0.0.0/0\",\"FromPort\":22,\"ToPort\":22}",
    },
    high: {
      rule_id: "S3_PUBLIC_ACL",
      title: "Public S3 ACL detected",
      resource: `AWS::S3::Bucket.SyntheticPublicBucket${String(index).padStart(2, "0")}`,
      file_path: "sample_iac/scenarios/large_violations/synthetic_large_violations.tf",
      recommendation: "Use private ACLs and enforce public access blocks for S3 buckets.",
      evidence: "acl = \"public-read\"",
    },
    medium: {
      rule_id: "DATABASE_ENCRYPTION_DISABLED",
      title: "Database encryption disabled",
      resource: `AWS::RDS::DBInstance.SyntheticDatabase${String(index).padStart(2, "0")}`,
      file_path: "sample_iac/scenarios/large_violations/synthetic_large_violations.json",
      recommendation: "Enable storage encryption for database resources before deployment.",
      evidence: "\"StorageEncrypted\": false",
    },
    low: {
      rule_id: "S3_VERSIONING_DISABLED",
      title: "S3 versioning disabled",
      resource: `AWS::S3::Bucket.SyntheticSuspendedVersioningBucket${String(index).padStart(2, "0")}`,
      file_path: "sample_iac/scenarios/large_violations/synthetic_large_violations.tf",
      recommendation: "Enable S3 bucket versioning to improve recovery from accidental overwrite or deletion.",
      evidence: "status = \"Suspended\"",
    },
  };

  return {
    id,
    severity,
    line_number: 10 + index,
    ...catalog[severity],
    ...overrides,
  };
}

function makeFindings() {
  const severities = [
    ["critical", 14],
    ["high", 15],
    ["medium", 14],
    ["low", 12],
  ];
  const findings = [];
  let id = 1;
  for (const [severity, count] of severities) {
    for (let index = 1; index <= count; index += 1) {
      findings.push(makeFinding(id, severity, index));
      id += 1;
    }
  }
  for (let index = 1; index <= 12; index += 1) {
    findings.push(
      makeFinding(id, "critical", index, {
        rule_id: "HARDCODED_SECRET",
        title: "Hardcoded credential detected",
        resource: `Custom::SecretConfig.SyntheticSecretConfig${String(index).padStart(2, "0")}`,
        file_path: "sample_iac/scenarios/large_violations/synthetic_large_violations.json",
        recommendation:
          "Remove the hardcoded credential, rotate the exposed value, and load it from a secrets manager or CI secret.",
        evidence: "AdminPassword = <redacted>",
      }),
    );
    id += 1;
  }
  return findings;
}

export function sampleScan(overrides = {}) {
  const findings = overrides.findings || makeFindings();
  return {
    id: 101,
    label: "Sample local IaC scan",
    target_path: "/workspace/sample_iac",
    risk_score: 47,
    files_scanned: 10,
    findings_count: findings.length,
    created_at: createdAt,
    findings,
    ...overrides,
  };
}

export function uploadedScan(overrides = {}) {
  const findings = overrides.findings || [
    makeFinding(9001, "medium", 1, {
      resource: "aws_db_instance.uploaded",
      file_path: "uploaded-risky.tf",
    }),
  ];
  return {
    id: 202,
    label: "Uploaded IaC scan",
    target_path: "uploaded: uploaded-risky.tf",
    risk_score: 90,
    files_scanned: 1,
    findings_count: findings.length,
    created_at: createdAt,
    findings,
    ...overrides,
  };
}

export function scenarioScans() {
  return [
    scenarioScan("both_risky", {
      id: 801,
      risk_score: 60,
      files_scanned: 2,
      created_at: "2026-06-22T22:10:00",
      findings: [
        makeFinding(80101, "critical", 1),
        makeFinding(80102, "high", 1),
        makeFinding(80103, "medium", 1),
      ],
    }),
    scenarioScan("terraform_only", {
      id: 802,
      risk_score: 73,
      files_scanned: 2,
      created_at: "2026-06-22T22:00:00",
      findings: [makeFinding(80201, "high", 1), makeFinding(80202, "medium", 1)],
    }),
    scenarioScan("json_only", {
      id: 803,
      risk_score: 60,
      files_scanned: 2,
      created_at: "2026-06-22T21:50:00",
      findings: [
        makeFinding(80301, "critical", 1),
        makeFinding(80302, "high", 1, {
          rule_id: "IAM_WILDCARD_POLICY",
          title: "Wildcard IAM policy detected",
          resource: "AWS::IAM::Role.AdminRole",
          file_path: "sample_iac/scenarios/json_only/risky_cloudformation.json",
          recommendation: "Replace wildcard actions and resources with least-privilege permissions.",
          evidence: "\"Action\" and \"Resource\" both include \"*\"",
        }),
      ],
    }),
    scenarioScan("clean", {
      id: 804,
      risk_score: 100,
      files_scanned: 2,
      created_at: "2026-06-22T21:40:00",
      findings: [],
    }),
    scenarioScan("large_violations", {
      id: 805,
      risk_score: 42,
      files_scanned: 2,
      created_at: "2026-06-22T21:30:00",
      findings: [
        ...Array.from({ length: 24 }, (_, index) => makeFinding(80500 + index, "critical", index + 1)),
        ...Array.from({ length: 12 }, (_, index) => makeFinding(80600 + index, "high", index + 1)),
        ...Array.from({ length: 12 }, (_, index) => makeFinding(80700 + index, "medium", index + 1)),
        ...Array.from({ length: 12 }, (_, index) => makeFinding(80800 + index, "low", index + 1)),
      ],
    }),
  ];
}

function scenarioScan(name, overrides) {
  const findings = overrides.findings || [];
  return {
    id: overrides.id,
    label: `Scenario: ${name}`,
    target_path: `/workspace/sample_iac/scenarios/${name}`,
    risk_score: overrides.risk_score,
    files_scanned: overrides.files_scanned,
    findings_count: findings.length,
    created_at: overrides.created_at,
    findings,
  };
}

function scanSummary(scan) {
  return {
    id: scan.id,
    label: scan.label,
    risk_score: scan.risk_score,
    findings_count: scan.findings_count,
    created_at: scan.created_at,
  };
}

function findingKey(finding) {
  return [
    finding.rule_id,
    finding.severity,
    finding.title,
    finding.file_path,
    finding.line_number,
    finding.resource,
  ].join("|");
}

function countBySeverity(findings) {
  return findings.reduce(
    (counts, finding) => ({
      ...counts,
      [finding.severity]: (counts[finding.severity] || 0) + 1,
    }),
    { critical: 0, high: 0, medium: 0, low: 0 },
  );
}

function diffFindings(baseFindings, headFindings) {
  const baseKeys = new Map();
  for (const finding of baseFindings) {
    const key = findingKey(finding);
    baseKeys.set(key, (baseKeys.get(key) || 0) + 1);
  }

  const newFindings = [];
  for (const finding of headFindings) {
    const key = findingKey(finding);
    const count = baseKeys.get(key) || 0;
    if (count > 0) {
      baseKeys.set(key, count - 1);
    } else {
      newFindings.push(finding);
    }
  }

  const headKeys = new Map();
  for (const finding of headFindings) {
    const key = findingKey(finding);
    headKeys.set(key, (headKeys.get(key) || 0) + 1);
  }

  const resolvedFindings = [];
  for (const finding of baseFindings) {
    const key = findingKey(finding);
    const count = headKeys.get(key) || 0;
    if (count > 0) {
      headKeys.set(key, count - 1);
    } else {
      resolvedFindings.push(finding);
    }
  }

  return { newFindings, resolvedFindings };
}

function summaryFor(newCounts, resolvedFindings) {
  if (newCounts.critical > 0) {
    return `Regression detected: this scan introduced ${newCounts.critical} new ${
      newCounts.critical === 1 ? "critical" : "criticals"
    }.`;
  }
  const newTotal = Object.values(newCounts).reduce((total, count) => total + count, 0);
  if (newTotal > 0) {
    return `Change detected: this scan introduced ${newTotal} new ${
      newTotal === 1 ? "finding" : "findings"
    }, with no new criticals.`;
  }
  if (resolvedFindings.length > 0) {
    return "No regression detected: this scan only resolved existing findings.";
  }
  return "No finding changes detected.";
}

export function compareScanPayload(baseScan, headScan) {
  const { newFindings, resolvedFindings } = diffFindings(baseScan.findings, headScan.findings);
  const baseCounts = countBySeverity(baseScan.findings);
  const headCounts = countBySeverity(headScan.findings);
  const newCounts = countBySeverity(newFindings);
  const resolvedCounts = countBySeverity(resolvedFindings);
  const severities = ["critical", "high", "medium", "low"];

  return {
    base_scan: scanSummary(baseScan),
    head_scan: scanSummary(headScan),
    risk_score_delta: headScan.risk_score - baseScan.risk_score,
    findings_count_delta: headScan.findings_count - baseScan.findings_count,
    new_findings_count: newFindings.length,
    resolved_findings_count: resolvedFindings.length,
    severity_deltas: severities.map((severity) => ({
      severity,
      base: baseCounts[severity],
      head: headCounts[severity],
      delta: headCounts[severity] - baseCounts[severity],
      new: newCounts[severity],
      resolved: resolvedCounts[severity],
    })),
    regression_summary: summaryFor(newCounts, resolvedFindings),
    new_findings: newFindings,
    resolved_findings: resolvedFindings,
  };
}

export async function fulfillJson(route, payload, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
}

export async function mockScanHistory(page, scans = []) {
  await page.route("**/api/scans/compare?*", async (route) => {
    const url = new URL(route.request().url());
    const baseId = Number(url.searchParams.get("base_scan_id"));
    const headId = Number(url.searchParams.get("head_scan_id"));
    const baseScan = scans.find((scan) => scan.id === baseId);
    const headScan = scans.find((scan) => scan.id === headId);
    if (!baseScan || !headScan) {
      await fulfillJson(route, { detail: "Scan not found" }, 404);
      return;
    }
    await fulfillJson(route, compareScanPayload(baseScan, headScan));
  });

  await page.route("**/api/scans", async (route) => {
    if (route.request().method() === "GET") {
      await fulfillJson(route, scans);
      return;
    }
    await route.fallback();
  });
}

export function trackFrontendErrors(page) {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(message.text());
    }
  });
  return errors;
}

export function expectNoFrontendErrors(errors) {
  expect(errors).toEqual([]);
}

export function expectOnlyExpectedResourceErrors(errors, statuses) {
  const allowedStatuses = statuses.join("|");
  const allowedPattern = new RegExp(
    `^Failed to load resource: the server responded with a status of (${allowedStatuses}) `,
  );
  expect(errors.filter((error) => !allowedPattern.test(error))).toEqual([]);
}
