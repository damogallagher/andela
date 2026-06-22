import { expect, test } from "@playwright/test";

import {
  expectNoFrontendErrors,
  expectOnlyExpectedResourceErrors,
  fulfillJson,
  mockScanHistory,
  trackFrontendErrors,
  uploadedScan,
} from "./fixtures/scans.js";

test.describe("dashboard upload scan form", () => {
  test("uploads one or more files and replaces the latest scan", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    const uploaded = uploadedScan({ label: "Uploaded risky scan" });
    await mockScanHistory(page, []);
    await page.route("**/api/scans/upload", async (route) => {
      expect(route.request().method()).toBe("POST");
      expect(route.request().headers()["content-type"]).toContain("multipart/form-data");
      await new Promise((resolve) => {
        setTimeout(resolve, 150);
      });
      await fulfillJson(route, uploaded);
    });

    await page.goto("/");
    await page.getByLabel("Scan label").fill("Uploaded risky scan");
    await page.getByLabel("Infrastructure files").setInputFiles([
      {
        name: "uploaded-risky.tf",
        mimeType: "text/plain",
        buffer: Buffer.from('resource "aws_db_instance" "uploaded" { storage_encrypted = false }'),
      },
      {
        name: "uploaded-clean.json",
        mimeType: "application/json",
        buffer: Buffer.from("{\"Resources\":{}}"),
      },
    ]);

    await page.getByRole("button", { name: "Scan Upload" }).click();

    await expect(page.getByRole("button", { name: "Scanning..." })).toBeVisible();
    await expect(page.getByRole("status")).toHaveText("Scan complete.");
    await expect(page.getByText("1 findings across 1 files")).toBeVisible();
    await expect(page.getByRole("button", { name: /Medium\s+1/ })).toBeVisible();
    await expect(page.getByText("Uploaded risky scan")).toBeVisible();
    await expect(page.locator("tbody tr").first()).toContainText("uploaded-risky.tf");
    expectNoFrontendErrors(frontendErrors);
  });

  test("shows upload validation errors from the API", async ({ page }) => {
    const frontendErrors = trackFrontendErrors(page);
    await mockScanHistory(page, []);
    await page.route("**/api/scans/upload", async (route) => {
      await fulfillJson(route, { detail: "Unsupported upload type for: notes.txt" }, 400);
    });

    await page.goto("/");
    await page.getByLabel("Infrastructure files").setInputFiles({
      name: "notes.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("not infrastructure"),
    });
    await page.getByRole("button", { name: "Scan Upload" }).click();

    await expect(page.getByRole("status")).toHaveText("Unsupported upload type for: notes.txt");
    await expect(page.getByRole("heading", { name: "No scan" })).toBeVisible();
    await expect(page.getByText("No scan history yet.")).toBeVisible();
    expectOnlyExpectedResourceErrors(frontendErrors, ["400"]);
  });
});
