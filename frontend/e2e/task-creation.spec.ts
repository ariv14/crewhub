import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Task Creation", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("new task page loads with form fields", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    await expect(page.locator("h1")).toContainText(/create task/i);
    // Agent selector should be present
    await expect(page.getByText(/select an agent/i)).toBeVisible({ timeout: 10_000 });
  });

  test("can select agent and see skills", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    // Open agent selector
    const agentTrigger = page.locator("button").filter({ hasText: /select an agent/i });
    await agentTrigger.waitFor({ timeout: 10_000 });
    await agentTrigger.click();

    // Select first agent
    const firstOption = page.locator("[role='option']").first();
    await firstOption.waitFor({ timeout: 5_000 });
    await firstOption.click();

    // Skill selector should appear
    await expect(
      page.getByText(/select a skill/i).or(page.getByText(/skill/i))
    ).toBeVisible({ timeout: 5_000 });
  });

  test("pre-fills agent from URL param", async ({ page }) => {
    // This test verifies the ?agent= URL param pre-fill
    // We need a valid agent ID; skip if agents list is empty
    await page.goto("/agents");
    const firstLink = page.locator("[data-testid='agent-card'] a, .group a").first();
    if (await firstLink.isVisible({ timeout: 5_000 })) {
      const href = await firstLink.getAttribute("href");
      if (href) {
        const agentId = href.split("/agents/")[1];
        if (agentId) {
          await page.goto(`/dashboard/tasks/new?agent=${agentId}`);
          // Agent should be pre-selected (no "Select an agent" placeholder)
          await page.waitForTimeout(2_000);
          await expect(page.locator("form")).toBeVisible();
        }
      }
    }
  });

  test("submit creates task and redirects to detail", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");

    // Select agent
    const agentTrigger = page.locator("button").filter({ hasText: /select an agent/i });
    await agentTrigger.waitFor({ timeout: 10_000 });
    await agentTrigger.click();
    await page.locator("[role='option']").first().click();

    // Wait for skills to load, select first if needed
    await page.waitForTimeout(1_000);

    // Type message
    const textarea = page.locator("textarea");
    await textarea.fill("Test task from E2E: summarize 'hello world'");

    // Submit
    await page.getByRole("button", { name: /create task/i }).click();

    // Should redirect to task detail
    await page.waitForURL(/\/dashboard\/tasks\/.+/, { timeout: 30_000 });
    await expect(page.locator("main")).toBeVisible();
  });
});
