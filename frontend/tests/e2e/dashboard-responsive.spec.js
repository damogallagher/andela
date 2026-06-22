import { expect, test } from "@playwright/test";

import { expectNoFrontendErrors, mockScanHistory, sampleScan, trackFrontendErrors } from "./fixtures/scans.js";

test.describe("dashboard responsive layout", () => {
  test("keeps core dashboard controls usable on mobile width", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    await page.setViewportSize({ width: 390, height: 900 });
    await mockScanHistory(page, [sampleScan()]);

    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Enterprise Security Guardrail Auditor" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Run Sample Scan" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Critical\s+14/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Scan Files" })).toBeVisible();
    await expect(page.getByPlaceholder("Search rule, resource, file, or recommendation")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Findings pagination" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recent Scans" })).toBeVisible();
    expectNoFrontendErrors(frontendErrors);
  });
});
