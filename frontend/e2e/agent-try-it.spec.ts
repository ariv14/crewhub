import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Agent Try It", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("Try It panel submits task and shows result", async ({ page }) => {
    // Navigate to first available (non-unavailable) agent
    await page.goto("/agents");
    // Find an agent card that has a "Try" button (not "Offline")
    const tryLink = page.locator("main a[href*='?tab=try']").first();
    const hasTryAgent = await tryLink.isVisible({ timeout: 10_000 }).catch(() => false);
    if (!hasTryAgent) {
      test.skip(true, "No available agents with Try button on staging");
      return;
    }
    await tryLink.click();
    await page.waitForURL(/\/agents\/[0-9a-f-]+/, { timeout: 10_000 });

    // "Try It" tab should be active from the URL
    const input = page.getByPlaceholder(/message/i);
    await input.waitFor({ timeout: 10_000 });
    await input.fill("Hello, please summarize this: The quick brown fox jumps over the lazy dog.");
    await page.getByRole("button").filter({ has: page.locator("svg") }).last().click();

    // Wait for any indication that a task was created or is in progress (90s for cold start)
    await expect(
      page.getByText(/working/i).or(page.getByText(/completed/i)).or(page.getByText(/submitted/i)).or(page.getByText(/created/i)).first()
    ).toBeVisible({ timeout: 90_000 });
  });
});
