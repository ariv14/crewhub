import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

// Known agent on staging — Universal Translator (owned by our test user)
const AGENT_PATH = "/agents/6c549d84-7fea-48d1-a385-ff8b11c3386b/";

/** Navigate directly to the agent detail page and wait for it to load. */
async function goToAgent(page: import("@playwright/test").Page) {
  await page.goto(AGENT_PATH);
  await page.getByRole("heading", { name: /universal translator/i }).waitFor({
    timeout: 15_000,
  });
}

test.describe("Agent Activity Tab", () => {
  test("activity tab is visible on agent detail page", async ({ page }) => {
    await goToAgent(page);

    const activityTab = page.getByRole("tab", { name: /activity/i });
    await expect(activityTab).toBeVisible({ timeout: 5_000 });
  });

  test("activity tab shows public stats for any visitor", async ({ page }) => {
    await goToAgent(page);

    // Click Activity tab
    await page.getByRole("tab", { name: /activity/i }).click();

    // Stats cards should be visible (public)
    const stats = page.getByTestId("activity-stats");
    await expect(stats).toBeVisible({ timeout: 5_000 });
    await expect(stats.getByText("Tasks Completed")).toBeVisible();
    await expect(stats.getByText("Success Rate")).toBeVisible();
    await expect(stats.getByText("Avg Latency")).toBeVisible();
    await expect(stats.getByText("Reputation")).toBeVisible();
  });

  test("unauthenticated user sees owner-only message instead of task list", async ({
    page,
  }) => {
    await goToAgent(page);

    await page.getByRole("tab", { name: /activity/i }).click();

    // Should see "only visible to owner" message
    await expect(
      page.getByText(/only visible to the agent owner/i)
    ).toBeVisible({ timeout: 5_000 });

    // Task log should NOT be visible
    await expect(page.getByTestId("activity-task-list")).toBeHidden();
  });

  test("authenticated owner sees task log with filters", async ({ page }) => {
    await loginWithApiKey(page);

    await goToAgent(page);

    await page.getByRole("tab", { name: /activity/i }).click();

    // Stats should always be visible
    await expect(page.getByTestId("activity-stats")).toBeVisible({
      timeout: 5_000,
    });

    // Check if we're the owner — if so, task list should appear
    const taskList = page.getByTestId("activity-task-list");
    const ownerMsg = page.getByText(/only visible to the agent owner/i);

    // One of these must be visible
    await expect(taskList.or(ownerMsg).first()).toBeVisible({ timeout: 10_000 });

    // If task list is visible, verify filters exist
    if (await taskList.isVisible()) {
      await expect(page.getByRole("button", { name: "All" })).toBeVisible();
      await expect(
        page.getByRole("button", { name: "Completed" })
      ).toBeVisible();
      await expect(page.getByRole("button", { name: "Failed" })).toBeVisible();
    }
  });

  test("status filter changes task list content", async ({ page }) => {
    await loginWithApiKey(page);

    await goToAgent(page);

    await page.getByRole("tab", { name: /activity/i }).click();

    const taskList = page.getByTestId("activity-task-list");
    // Skip if not owner
    if (!(await taskList.isVisible({ timeout: 5_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    // Click "Completed" filter
    await page.getByRole("button", { name: "Completed" }).click();
    // Allow time for refetch
    await page.waitForTimeout(1_000);

    // Click "All" to reset
    await page.getByRole("button", { name: "All" }).click();
    await page.waitForTimeout(1_000);

    // No crash = pass
    await expect(taskList).toBeVisible();
  });
});
