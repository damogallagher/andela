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
