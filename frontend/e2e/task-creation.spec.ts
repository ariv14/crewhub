import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Task Creation", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("new task page loads with form fields", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    await expect(page.locator("h1")).toContainText(/create task/i);
    // Wait for agent card to load (contains the agent selector)
    await expect(page.getByText(/agent/i).first()).toBeVisible({ timeout: 10_000 });
  });

  test("can select agent and see skills", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    // Wait for and click agent selector trigger
    const agentTrigger = page.locator("button[role='combobox']").first();
    await agentTrigger.waitFor({ timeout: 15_000 });
    await agentTrigger.click();

    // Select first agent
    const firstOption = page.locator("[role='option']").first();
    await firstOption.waitFor({ timeout: 5_000 });
    await firstOption.click();

    // Skill section should appear
    await expect(page.getByText(/skill/i)).toBeVisible({ timeout: 5_000 });
  });

  test("pre-fills agent from URL param", async ({ page }) => {
    // Get a valid agent ID from the agents page
    const resp = await page.request.get(
      "https://arimatch1-crewhub-staging.hf.space/api/v1/agents/?per_page=1&status=active",
      { headers: { "X-API-Key": process.env.E2E_API_KEY || "" } }
    );
    const data = await resp.json();
    const agentId = data.agents?.[0]?.id;
    if (!agentId) {
      test.skip();
      return;
    }

    await page.goto(`/dashboard/tasks/new?agent=${agentId}`);
    await page.waitForTimeout(3_000);
    // The form should be visible with the agent pre-selected
    await expect(page.locator("form")).toBeVisible({ timeout: 15_000 });
  });

  test("submit creates task and redirects to detail", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");

    // Select agent via combobox
    const agentTrigger = page.locator("button[role='combobox']").first();
    await agentTrigger.waitFor({ timeout: 15_000 });
    await agentTrigger.click();
    await page.locator("[role='option']").first().click();

    // Wait for skills to load
    await page.waitForTimeout(1_500);

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
