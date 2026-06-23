import { expect, test } from "@playwright/test";

import { expectNoFrontendErrors, mockScanHistory, scenarioScans, trackFrontendErrors } from "./fixtures/scans.js";

const scenarioExpectations = [
  {
    label: "Scenario: both_risky",
    score: 60,
    detail: "3 findings across 2 files",
    matching: "3 matching findings",
    counts: { critical: 1, high: 1, medium: 1, low: 0 },
  },
  {
    label: "Scenario: terraform_only",
    score: 73,
    detail: "2 findings across 2 files",
    matching: "2 matching findings",
    counts: { critical: 0, high: 1, medium: 1, low: 0 },
  },
  {
    label: "Scenario: json_only",
    score: 60,
    detail: "2 findings across 2 files",
    matching: "2 matching findings",
    counts: { critical: 1, high: 1, medium: 0, low: 0 },
  },
  {
    label: "Scenario: clean",
    score: 100,
    detail: "0 findings across 2 files",
    matching: null,
    counts: { critical: 0, high: 0, medium: 0, low: 0 },
  },
  {
    label: "Scenario: large_violations",
    score: 42,
    detail: "60 findings across 2 files",
    matching: "60 matching findings",
    counts: { critical: 24, high: 12, medium: 12, low: 12 },
  },
];

test.describe("dashboard sample_iac scenario coverage", () => {
  test("selects each sample_iac scenario from recent scans and renders its findings", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    await mockScanHistory(page, scenarioScans());

    await page.goto("/");

    for (const scenario of scenarioExpectations) {
      await page.getByRole("button", { name: new RegExp(`${scenario.label}\\s+${scenario.score}`) }).click();

      await expect(page.locator("#score-title")).toHaveText(`${scenario.score}%`);
      await expect(page.getByText(scenario.detail)).toBeVisible();
      await expect(page.getByRole("button", { name: new RegExp(`Critical\\s+${scenario.counts.critical}`) })).toBeVisible();
      await expect(page.getByRole("button", { name: new RegExp(`High\\s+${scenario.counts.high}`) })).toBeVisible();
      await expect(page.getByRole("button", { name: new RegExp(`Medium\\s+${scenario.counts.medium}`) })).toBeVisible();
      await expect(page.getByRole("button", { name: new RegExp(`Low\\s+${scenario.counts.low}`) })).toBeVisible();

      if (scenario.matching) {
        await expect(page.getByText(scenario.matching)).toBeVisible();
        await expect(page.getByRole("region", { name: "Scrollable findings table" })).toBeVisible();
      } else {
        await expect(page.getByText("No findings available yet.")).toBeVisible();
      }
    }

    expectNoFrontendErrors(frontendErrors);
  });
});
