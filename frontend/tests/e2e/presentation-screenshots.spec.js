import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { mockScanHistory, sampleScan, uploadedScan } from "./fixtures/scans.js";

const currentFile = fileURLToPath(import.meta.url);
const screenshotsDir = path.resolve(path.dirname(currentFile), "../../..", "screenshots");

test.describe("presentation screenshots", () => {
  test.skip(process.env.CAPTURE_PRESENTATION_SCREENSHOTS !== "1", "Set CAPTURE_PRESENTATION_SCREENSHOTS=1.");

  test("captures dashboard states for the presentation deck", async ({ page }) => {
    const latestScan = sampleScan({
      id: 910,
      label: "Presentation sample scan",
      created_at: "2026-06-22T22:35:00",
    });
    const previousScan = uploadedScan({
      id: 911,
      label: "Presentation upload baseline",
      risk_score: 90,
      created_at: "2026-06-22T21:20:00",
    });
    await fs.mkdir(screenshotsDir, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 1200 });
    await mockScanHistory(page, [latestScan, previousScan]);

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Enterprise Security Guardrail Auditor" })).toBeVisible();
    await expect(page.getByText("Regression detected: this scan introduced 26 new criticals.")).toBeVisible();
    await page.screenshot({ path: path.join(screenshotsDir, "dashboard-overview.png"), fullPage: true });

    await page.getByRole("button", { name: /Critical\s+26/ }).click();
    await expect(page.getByText("26 matching findings")).toBeVisible();
    await page.screenshot({ path: path.join(screenshotsDir, "severity-filter-critical.png"), fullPage: true });

    await page.getByRole("button", { name: "Clear" }).click();
    await page.getByPlaceholder("Search rule, resource, file, or recommendation").fill("SyntheticOpenSshSecurityGroup03");
    await expect(page.getByText("1 matching finding")).toBeVisible();
    await page.screenshot({ path: path.join(screenshotsDir, "findings-search.png"), fullPage: true });
  });
});
