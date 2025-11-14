import { test, expect } from "@playwright/test";

test("home renders and primary sections visible", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "OKLab Web App: Geometric Semantics" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "OKLab Playground" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "OKLCh Controls" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "OKLab Mixer" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "IR Panel" })).toBeVisible();
});
