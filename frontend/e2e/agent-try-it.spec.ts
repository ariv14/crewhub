import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Agent Try It", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("Try It panel submits task and shows result", async ({ page }) => {
    // Navigate to first agent detail
    await page.goto("/agents");
    const firstCard = page.locator("[data-testid='agent-card'], .group a").first();
    await firstCard.waitFor({ timeout: 10_000 });
    await firstCard.click();
    await page.waitForURL(/\/agents\/.+/);

    // Click "Try It" tab
    const tryItTab = page.getByRole("tab", { name: /try/i });
    if (await tryItTab.isVisible()) {
      await tryItTab.click();
    }

    // Type a message and submit
    const input = page.getByPlaceholder(/message/i);
    await input.waitFor({ timeout: 5_000 });
    await input.fill("Hello, please summarize this: The quick brown fox jumps over the lazy dog.");
    await page.getByRole("button").filter({ has: page.locator("svg") }).last().click();

    // Wait for response (task polling)
    await expect(
      page.locator("text=Agent is working").or(page.locator("[class*='artifact']")).first()
    ).toBeVisible({ timeout: 30_000 });
  });
});
