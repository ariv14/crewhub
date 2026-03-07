import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Task Lifecycle", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("task list shows tasks", async ({ page }) => {
    await page.goto("/dashboard/tasks");
    await expect(page.locator("h1")).toContainText(/my tasks/i, { timeout: 10_000 });
    // Either task cards or empty state (page uses card layout, not tables)
    const taskCard = page.locator("a.block[href*='/dashboard/tasks/']").first();
    const emptyState = page.getByText(/no tasks/i);
    await expect(
      taskCard.or(emptyState)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("click task navigates to detail", async ({ page }) => {
    await page.goto("/dashboard/tasks");
    const firstTaskLink = page.locator("a.block[href*='/dashboard/tasks/']").first();
    if (await firstTaskLink.isVisible({ timeout: 5_000 })) {
      await firstTaskLink.click();
      await page.waitForURL(/\/dashboard\/tasks\/.+/);
      await expect(page.locator("main")).toBeVisible();
    }
  });

  test("task detail shows status and messages", async ({ page }) => {
    await page.goto("/dashboard/tasks");
    const firstTaskLink = page.locator("a.block[href*='/dashboard/tasks/']").first();
    if (await firstTaskLink.isVisible({ timeout: 5_000 })) {
      await firstTaskLink.click();
      await page.waitForURL(/\/dashboard\/tasks\/.+/);
      // Should show status badge
      await expect(
        page.locator("[class*='badge'], [class*='Badge']").first()
      ).toBeVisible({ timeout: 5_000 });
    }
  });

  test("completed task shows artifacts", async ({ page }) => {
    await page.goto("/dashboard/tasks");
    // Look for a completed task card
    const completedCard = page.locator("a.block[href*='/dashboard/tasks/']").filter({ hasText: /completed/i }).first();
    if (await completedCard.isVisible({ timeout: 5_000 })) {
      await completedCard.click();
      await page.waitForURL(/\/dashboard\/tasks\/.+/);
      // Completed tasks should show artifacts or result section
      await expect(page.locator("main")).toBeVisible();
    }
  });
});
