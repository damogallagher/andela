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
    await expect(page.getByRole("button", { name: /Critical\s+26/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Scan Files" })).toBeVisible();
    await expect(page.getByPlaceholder("Search rule, resource, file, or recommendation")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Findings pagination" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recent Scans" })).toBeVisible();

    const tableRegion = page.getByRole("region", { name: "Scrollable findings table" });
    const scrollMetrics = await tableRegion.evaluate((element) => ({
      clientWidth: element.clientWidth,
      scrollWidth: element.scrollWidth,
    }));
    expect(scrollMetrics.scrollWidth).toBeGreaterThan(scrollMetrics.clientWidth);
    expectNoFrontendErrors(frontendErrors);
  });

  test("places recent scans to the right of findings on desktop width", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "Desktop rail assertion only applies to the desktop project.");
    const frontendErrors = trackFrontendErrors(page);
    await page.setViewportSize({ width: 1440, height: 900 });
    await mockScanHistory(page, [sampleScan()]);

    await page.goto("/");
    await expect(page.getByRole("region", { name: "Findings", exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "Recent Scans" })).toBeVisible();

    const findingsBox = await page.locator('section[aria-labelledby="findings-title"]').boundingBox();
    const historyBox = await page.locator('section[aria-labelledby="history-title"]').boundingBox();

    expect(findingsBox).not.toBeNull();
    expect(historyBox).not.toBeNull();
    expect(historyBox.x).toBeGreaterThan(findingsBox.x + findingsBox.width - 1);
    expect(Math.abs(historyBox.y - findingsBox.y)).toBeLessThan(24);
    expectNoFrontendErrors(frontendErrors);
  });
});
