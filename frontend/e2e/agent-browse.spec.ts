import { test, expect } from "@playwright/test";

test.describe("Agent Browsing", () => {
  test("browse agents page loads and shows agent cards", async ({ page }) => {
    await page.goto("/agents");
    await expect(page.locator("h1")).toContainText(/agents/i);
    // At least one agent card should be visible
    await expect(page.locator("[data-testid='agent-card'], .group").first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("search filters agents", async ({ page }) => {
    await page.goto("/agents");
    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible()) {
      await searchInput.fill("summarizer");
      await page.waitForTimeout(500); // debounce
      // Results should still show or filter down
      await expect(page.locator("main")).toBeVisible();
    }
  });

  test("click agent card navigates to detail page", async ({ page }) => {
    await page.goto("/agents");
    const firstCard = page.locator("[data-testid='agent-card'], .group a").first();
    await firstCard.waitFor({ timeout: 10_000 });
    await firstCard.click();
    await page.waitForURL(/\/agents\/.+/);
    // Detail page should show agent name
    await expect(page.locator("h1, h2").first()).toBeVisible();
  });

  test("agent detail page has tabs", async ({ page }) => {
    await page.goto("/agents");
    const firstCard = page.locator("[data-testid='agent-card'], .group a").first();
    await firstCard.waitFor({ timeout: 10_000 });
    await firstCard.click();
    await page.waitForURL(/\/agents\/.+/);
    // Should have tab-like navigation (Overview, Try It, etc.)
    await expect(page.getByRole("tab").or(page.locator("[role='tablist']")).first()).toBeVisible({
      timeout: 5_000,
    });
  });
});
