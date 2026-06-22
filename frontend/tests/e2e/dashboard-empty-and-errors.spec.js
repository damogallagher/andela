import { expect, test } from "@playwright/test";

import {
  expectNoFrontendErrors,
  expectOnlyExpectedResourceErrors,
  fulfillJson,
  mockScanHistory,
  trackFrontendErrors,
} from "./fixtures/scans.js";

test.describe("dashboard empty, loading, and API error states", () => {
  test("renders the empty dashboard and primary navigation", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    await mockScanHistory(page, []);

    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Enterprise Security Guardrail Auditor" })).toBeVisible();
    await expect(page.getByText("Local-only security scanner")).toBeVisible();
    await expect(page.getByRole("button", { name: "Run Sample Scan" })).toBeEnabled();
    await expect(page.getByRole("link", { name: "API Docs" })).toHaveAttribute("href", "/docs");
    await expect(page.getByRole("heading", { name: "No scan" })).toBeVisible();
    await expect(page.getByText("Run the sample scan to populate the dashboard.")).toBeVisible();
    await expect(page.getByRole("button", { name: /Critical\s+0/ })).toHaveAttribute("aria-pressed", "false");
    await expect(page.getByRole("button", { name: /High\s+0/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Medium\s+0/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Low\s+0/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Scan Files" })).toBeVisible();
    await expect(page.getByText("No findings available yet.")).toBeVisible();
    await expect(page.getByText("No scan history yet.")).toBeVisible();
    expectNoFrontendErrors(frontendErrors);
  });

  test("shows the loading state before scan history returns", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    await page.route("**/api/scans", async (route) => {
      await new Promise((resolve) => {
        setTimeout(resolve, 250);
      });
      await fulfillJson(route, []);
    });

    await page.goto("/");

    await expect(page.getByText("Loading scans...")).toBeVisible();
    await expect(page.getByRole("heading", { name: "No scan" })).toBeVisible();
    await expect(page.getByText("Loading scans...")).toBeHidden();
    expectNoFrontendErrors(frontendErrors);
  });

  test("shows an alert when scan history cannot be loaded", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    await page.route("**/api/scans", async (route) => {
      await fulfillJson(route, { detail: "Scan history unavailable" }, 503);
    });

    await page.goto("/");

    await expect(page.getByRole("alert")).toHaveText("Scan history unavailable");
    await expect(page.getByRole("heading", { name: "No scan" })).toBeVisible();
    expectOnlyExpectedResourceErrors(frontendErrors, ["503"]);
  });
});
