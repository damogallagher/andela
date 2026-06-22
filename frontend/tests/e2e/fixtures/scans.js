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
  return findings;
}

export function sampleScan(overrides = {}) {
  const findings = overrides.findings || makeFindings();
  return {
    id: 101,
    label: "Sample local IaC scan",
    target_path: "/workspace/sample_iac",
    risk_score: 0,
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

export async function fulfillJson(route, payload, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
}

export async function mockScanHistory(page, scans = []) {
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
