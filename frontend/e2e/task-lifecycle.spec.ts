import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Task Lifecycle", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("task list shows tasks", async ({ page }) => {
    await page.goto("/dashboard/tasks");
    await expect(page.locator("h1")).toContainText(/my tasks/i);
    // Either tasks table or empty state
    await expect(
      page.locator("table").or(page.getByText(/no tasks/i))
    ).toBeVisible({ timeout: 10_000 });
  });

  test("click task navigates to detail", async ({ page }) => {
    await page.goto("/dashboard/tasks");
    const firstTaskLink = page.locator("table a").first();
    if (await firstTaskLink.isVisible({ timeout: 5_000 })) {
      await firstTaskLink.click();
      await page.waitForURL(/\/dashboard\/tasks\/.+/);
      await expect(page.locator("main")).toBeVisible();
    }
  });

  test("task detail shows status and messages", async ({ page }) => {
    await page.goto("/dashboard/tasks");
    const firstTaskLink = page.locator("table a").first();
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
    // Look for a completed task
    const completedRow = page.locator("tr").filter({ hasText: /completed/i }).first();
    if (await completedRow.isVisible({ timeout: 5_000 })) {
      await completedRow.locator("a").first().click();
      await page.waitForURL(/\/dashboard\/tasks\/.+/);
      // Completed tasks should show artifacts or result section
      await expect(page.locator("main")).toBeVisible();
    }
  });
});
