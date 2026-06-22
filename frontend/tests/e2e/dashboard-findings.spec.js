import { expect, test } from "@playwright/test";

import {
  expectNoFrontendErrors,
  expectOnlyExpectedResourceErrors,
  fulfillJson,
  mockScanHistory,
  sampleScan,
  trackFrontendErrors,
  uploadedScan,
} from "./fixtures/scans.js";

test.describe("dashboard sample scan, filters, search, pagination, and history", () => {
  test("runs a sample scan and renders severity totals and recent history", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    const scan = sampleScan();
    await mockScanHistory(page, []);
    await page.route("**/api/scans/sample", async (route) => {
      expect(route.request().method()).toBe("POST");
      await new Promise((resolve) => {
        setTimeout(resolve, 150);
      });
      await fulfillJson(route, scan);
    });

    await page.goto("/");
    await page.getByRole("button", { name: "Run Sample Scan" }).click();

    await expect(page.getByRole("button", { name: "Scanning..." })).toBeVisible();
    await expect(page.getByText("55 findings across 10 files")).toBeVisible();
    await expect(page.getByRole("button", { name: /Critical\s+14/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /High\s+15/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Medium\s+14/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Low\s+12/ })).toBeVisible();
    await expect(page.getByText("55 matching findings")).toBeVisible();
    await expect(page.getByText("Page 1 of 11")).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(5);
    await expect(page.getByRole("heading", { name: "Recent Scans" })).toBeVisible();
    await expect(page.getByText("Sample local IaC scan")).toBeVisible();
    await expect(page.getByRole("button", { name: /Sample local IaC scan\s+0\s+2026-06-22 22:35/ })).toBeVisible();
    expectNoFrontendErrors(frontendErrors);
  });

  test("selects a recent scan and shows that scan's results", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    const currentScan = sampleScan({
      id: 301,
      label: "Current sample scan",
      created_at: "2026-06-22T22:35:00",
    });
    const previousScan = uploadedScan({
      id: 302,
      label: "Uploaded smoke scan",
      created_at: "2026-06-22T21:15:00",
    });
    await mockScanHistory(page, [currentScan, previousScan]);

    await page.goto("/");

    await expect(page.getByText("55 findings across 10 files")).toBeVisible();
    await expect(page.getByRole("button", { name: /Current sample scan\s+0\s+2026-06-22 22:35/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    const previousButton = page.getByRole("button", { name: /Uploaded smoke scan\s+90\s+2026-06-22 21:15/ });
    await previousButton.click();

    await expect(previousButton).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("1 findings across 1 files")).toBeVisible();
    await expect(page.getByRole("button", { name: /Critical\s+0/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Medium\s+1/ })).toBeVisible();
    await expect(page.getByText("1 matching finding")).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(1);
    await expect(page.locator("tbody tr").first()).toContainText("uploaded-risky.tf");
    await expect(page.locator('section[aria-labelledby="findings-title"]')).toContainText("2026-06-22 21:15");
    expectNoFrontendErrors(frontendErrors);
  });

  test("colors the score percentage by threshold", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    const greenScan = sampleScan({
      id: 401,
      label: "Green score scan",
      risk_score: 95,
    });
    const amberScan = sampleScan({
      id: 402,
      label: "Amber score scan",
      risk_score: 90,
    });
    const redScan = sampleScan({
      id: 403,
      label: "Red score scan",
      risk_score: 69,
    });
    await mockScanHistory(page, [greenScan, amberScan, redScan]);

    await page.goto("/");

    const score = page.locator("#score-title");
    await expect(score).toHaveText("95%");
    await expect(score).toHaveCSS("color", "rgb(21, 128, 61)");

    await page.getByRole("button", { name: /Amber score scan\s+90/ }).click();
    await expect(score).toHaveText("90%");
    await expect(score).toHaveCSS("color", "rgb(183, 121, 31)");

    await page.getByRole("button", { name: /Red score scan\s+69/ }).click();
    await expect(score).toHaveText("69%");
    await expect(score).toHaveCSS("color", "rgb(185, 28, 28)");
    expectNoFrontendErrors(frontendErrors);
  });

  test("filters findings by severity and clears the breadcrumb state", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    await mockScanHistory(page, [sampleScan()]);

    await page.goto("/");
    await page.getByRole("button", { name: /Low\s+12/ }).click();

    await expect(page.getByRole("button", { name: /Low\s+12/ })).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator('ol[aria-label="Current finding filter"]')).toContainText("All severities");
    await expect(page.locator('ol[aria-label="Current finding filter"]')).toContainText("Low");
    await expect(page.getByText("12 matching findings")).toBeVisible();
    await expect(page.getByText("Page 1 of 3")).toBeVisible();
    await expect(page.locator("tbody tr").first()).toContainText("low");

    await page.getByRole("button", { name: "Clear" }).click();

    await expect(page.getByRole("button", { name: /Low\s+12/ })).toHaveAttribute("aria-pressed", "false");
    await expect(page.locator('ol[aria-label="Current finding filter"]')).not.toContainText("Low");
    await expect(page.getByText("55 matching findings")).toBeVisible();
    expectNoFrontendErrors(frontendErrors);
  });

  test("searches findings, shows no-match state, changes page size, and paginates", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    await mockScanHistory(page, [sampleScan()]);

    await page.goto("/");

    const search = page.getByPlaceholder("Search rule, resource, file, or recommendation");
    await search.fill("SyntheticOpenSshSecurityGroup03");
    await expect(page.getByText("1 matching finding")).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(1);
    await expect(page.locator("tbody tr").first()).toContainText("SyntheticOpenSshSecurityGroup03");

    await search.fill("no-resource-matches-this-query");
    await expect(page.getByText("No findings match the current filters.")).toBeVisible();

    await search.fill("");
    await page.getByLabel("Rows").selectOption("10");
    await expect(page.locator("tbody tr")).toHaveCount(10);
    await expect(page.getByText("Page 1 of 6")).toBeVisible();

    await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText("Page 2 of 6")).toBeVisible();
    await expect(page.getByRole("button", { name: "Previous" })).toBeEnabled();

    await page.getByRole("button", { name: "Previous" }).click();
    await expect(page.getByText("Page 1 of 6")).toBeVisible();
    expectNoFrontendErrors(frontendErrors);
  });

  test("sorts findings from the table headers", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    await mockScanHistory(page, [
      sampleScan({
        findings_count: 3,
        files_scanned: 3,
        findings: [
          {
            id: 1,
            severity: "high",
            title: "Zeta wildcard policy",
            resource: "resource-z",
            file_path: "zeta.tf",
            line_number: 22,
            recommendation: "Use scoped permissions.",
            evidence: "*",
          },
          {
            id: 2,
            severity: "low",
            title: "Alpha versioning gap",
            resource: "resource-a",
            file_path: "alpha.tf",
            line_number: 4,
            recommendation: "Apply versioning.",
            evidence: "Suspended",
          },
          {
            id: 3,
            severity: "critical",
            title: "Middle SSH exposure",
            resource: "resource-m",
            file_path: "middle.tf",
            line_number: 8,
            recommendation: "Restrict SSH.",
            evidence: "0.0.0.0/0",
          },
        ],
      }),
    ]);

    await page.goto("/");

    await page.getByRole("button", { name: "Sort by Rule" }).click();
    await expect(page.locator("th").filter({ has: page.getByRole("button", { name: "Sort by Rule" }) })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
    await expect(page.locator("tbody tr").first()).toContainText("Alpha versioning gap");

    await page.getByRole("button", { name: "Sort by Resource" }).click();
    await expect(page.locator("tbody tr").first()).toContainText("resource-a");

    await page.getByRole("button", { name: "Sort by File" }).click();
    await expect(page.locator("tbody tr").first()).toContainText("alpha.tf:4");

    await page.getByRole("button", { name: "Sort by Recommendation" }).click();
    await expect(page.locator("tbody tr").first()).toContainText("Apply versioning.");

    await page.getByRole("button", { name: "Sort by Severity" }).click();
    await expect(page.locator("tbody tr").first()).toContainText("Middle SSH exposure");

    await page.getByRole("button", { name: "Sort by Severity" }).click();
    await expect(page.locator("th").filter({ has: page.getByRole("button", { name: "Sort by Severity" }) })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
    await expect(page.locator("tbody tr").first()).toContainText("Alpha versioning gap");
    expectNoFrontendErrors(frontendErrors);
  });

  test("shows a run-sample error without replacing the existing dashboard", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    await mockScanHistory(page, [sampleScan()]);
    await page.route("**/api/scans/sample", async (route) => {
      await fulfillJson(route, { detail: "Sample scan failed" }, 500);
    });

    await page.goto("/");
    await page.getByRole("button", { name: "Run Sample Scan" }).click();

    await expect(page.getByRole("alert")).toHaveText("Sample scan failed");
    await expect(page.getByText("55 findings across 10 files")).toBeVisible();
    expectOnlyExpectedResourceErrors(frontendErrors, ["500"]);
  });
});
