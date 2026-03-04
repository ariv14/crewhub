import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Task Creation", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("new task page loads with mode toggle", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    await expect(page.locator("h1")).toContainText(/create task/i);
    // Mode toggle buttons should be visible
    await expect(page.getByRole("button", { name: /auto/i })).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByRole("button", { name: /manual/i })).toBeVisible();
  });

  test("auto mode shows message textarea and find button", async ({
    page,
  }) => {
    await page.goto("/dashboard/tasks/new");
    // Auto mode is the default (no ?agent= param)
    await expect(page.getByText(/what do you need/i)).toBeVisible({
      timeout: 10_000,
    });
    await expect(
      page.getByRole("button", { name: /find best agent/i })
    ).toBeVisible();
  });

  test("can switch to manual mode and see agent selector", async ({
    page,
  }) => {
    await page.goto("/dashboard/tasks/new");
    // Click Manual mode
    await page.getByRole("button", { name: /manual/i }).click();
    // Agent selector should appear
    const agentTrigger = page.locator("button[role='combobox']").first();
    await agentTrigger.waitFor({ timeout: 10_000 });
    await expect(agentTrigger).toBeVisible();
  });

  test("can select agent and see skills in manual mode", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    // Switch to manual
    await page.getByRole("button", { name: /manual/i }).click();

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

  test("pre-fills agent from URL param and defaults to manual mode", async ({
    page,
  }) => {
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
    // With ?agent= param, manual mode should be active
    await expect(page.locator("form")).toBeVisible({ timeout: 15_000 });
    // Agent combobox should be visible (manual mode)
    await expect(
      page.locator("button[role='combobox']").first()
    ).toBeVisible();
  });

  test("submit creates task via manual mode and redirects to detail", async ({
    page,
  }) => {
    await page.goto("/dashboard/tasks/new");

    // Switch to manual mode
    await page.getByRole("button", { name: /manual/i }).click();

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
