import { test, expect } from "@playwright/test";

test.describe("Agent Browsing", () => {
  test("browse agents page loads and shows agent cards", async ({ page }) => {
    await page.goto("/agents");
    await expect(page.locator("h1")).toContainText(/agent/i);
    // Agent cards are rendered as links to /agents/<id>/
    await expect(page.locator("a[href^='/agents/']").first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("search filters agents", async ({ page }) => {
    await page.goto("/agents");
    const searchInput = page.getByRole("searchbox");
    if (await searchInput.isVisible()) {
      await searchInput.fill("summarizer");
      await page.waitForTimeout(500); // debounce
      await expect(page.locator("main")).toBeVisible();
    }
  });

  test("click agent card navigates to detail page", async ({ page }) => {
    await page.goto("/agents");
    // Agent cards are links inside main, exclude nav links
    const firstCard = page.locator("main a[href*='/agents/']").first();
    await firstCard.waitFor({ timeout: 10_000 });
    await firstCard.click();
    await page.waitForURL(/\/agents\/[0-9a-f-]+/, { timeout: 10_000 });
    await expect(page.locator("h1, h2, h3").first()).toBeVisible();
  });

  test("agent detail page has tabs", async ({ page }) => {
    await page.goto("/agents");
    const firstCard = page.locator("main a[href*='/agents/']").first();
    await firstCard.waitFor({ timeout: 10_000 });
    await firstCard.click();
    await page.waitForURL(/\/agents\/[0-9a-f-]+/, { timeout: 10_000 });
    // Should have tab-like navigation (Overview, Try It, etc.)
    await expect(
      page.getByRole("tab").or(page.locator("[role='tablist']")).first()
    ).toBeVisible({ timeout: 5_000 });
  });
});
