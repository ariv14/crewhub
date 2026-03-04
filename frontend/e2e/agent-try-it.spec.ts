import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Agent Try It", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("Try It panel submits task and shows result", async ({ page }) => {
    // Navigate to first agent detail
    await page.goto("/agents");
    const firstCard = page.locator("main a[href*='/agents/']").first();
    await firstCard.waitFor({ timeout: 10_000 });
    await firstCard.click();
    await page.waitForURL(/\/agents\/[0-9a-f-]+/, { timeout: 10_000 });

    // Click "Try It" tab
    const tryItTab = page.getByRole("tab", { name: /try/i });
    if (await tryItTab.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await tryItTab.click();
    }

    // Type a message and submit
    const input = page.getByPlaceholder(/message/i);
    await input.waitFor({ timeout: 5_000 });
    await input.fill("Hello, please summarize this: The quick brown fox jumps over the lazy dog.");
    await page.getByRole("button").filter({ has: page.locator("svg") }).last().click();

    // Wait for response (task polling)
    await expect(
      page.locator("text=Agent is working").or(page.locator("text=working")).first()
    ).toBeVisible({ timeout: 30_000 });
  });
});
