import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Task Creation", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("new task page loads with search input", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    await expect(page.locator("h1")).toContainText(/create task/i);
    await expect(
      page.getByPlaceholder(/search agents/i)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("search shows matching agents", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    const searchInput = page.getByPlaceholder(/search agents/i);
    await searchInput.waitFor({ timeout: 10_000 });
    await searchInput.fill("developer");
    // Wait for results to appear (debounced)
    await page.waitForTimeout(500);
    // Should see at least one agent card or a "no agents found" message
    const hasResults = await page
      .locator("button.rounded-lg")
      .first()
      .isVisible()
      .catch(() => false);
    const hasNoResults = await page
      .getByText(/no agents found/i)
      .isVisible()
      .catch(() => false);
    expect(hasResults || hasNoResults).toBeTruthy();
  });

  test("can select agent and see skills", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    const searchInput = page.getByPlaceholder(/search agents/i);
    await searchInput.waitFor({ timeout: 10_000 });

    // Search broadly to find any agent
    await searchInput.fill("agent");
    await page.waitForTimeout(1_000);

    // Click first agent result
    const firstAgent = page.locator("button.rounded-lg").first();
    if (await firstAgent.isVisible().catch(() => false)) {
      await firstAgent.click();
      // Skill section should appear
      await expect(page.getByText(/skill/i)).toBeVisible({ timeout: 5_000 });
    } else {
      test.skip();
    }
  });

  test("pre-fills agent from URL param", async ({ page }) => {
    // Get a valid agent ID from the agents API
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
    // With ?agent= param, agent should be pre-selected (no search input visible)
    await expect(page.getByRole("button", { name: /create task/i })).toBeVisible({
      timeout: 15_000,
    });
    // Search input should NOT be visible (agent already selected)
    await expect(page.getByPlaceholder(/search agents/i)).not.toBeVisible();
  });

  test("submit creates task and redirects to detail", async ({ page }) => {
    // Get a valid agent ID to pre-select
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

    // Wait for agent to load and skill section to appear
    await page.waitForTimeout(3_000);

    // Type message
    const textarea = page.locator("textarea");
    await textarea.waitFor({ timeout: 10_000 });
    await textarea.fill("Test task from E2E: summarize 'hello world'");

    // Submit
    await page.getByRole("button", { name: /create task/i }).click();

    // Should redirect to task detail
    await page.waitForURL(/\/dashboard\/tasks\/.+/, { timeout: 30_000 });
    await expect(page.locator("main")).toBeVisible();
  });
});
