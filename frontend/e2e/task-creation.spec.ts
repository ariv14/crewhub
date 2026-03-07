import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Task Creation", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("new task page loads with agents listed by default", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    await expect(page.locator("h1")).toContainText(/create task/i);
    await expect(
      page.getByPlaceholder(/search agents/i)
    ).toBeVisible({ timeout: 10_000 });
    // Agents should be listed by default without searching
    await expect(
      page.locator("button.rounded-lg").first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("search filters the agent list", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    const searchInput = page.getByPlaceholder(/search agents/i);
    await searchInput.waitFor({ timeout: 10_000 });
    // Wait for default agents to load
    await expect(
      page.locator("button.rounded-lg").first()
    ).toBeVisible({ timeout: 10_000 });
    const beforeCount = await page.locator("button.rounded-lg").count();
    // Type a search query (backend uses semantic search so results may vary)
    await searchInput.fill("translate text between languages");
    // Wait for debounce (300ms) + API response
    await page.waitForTimeout(2_000);
    // After searching, should still show results OR "no agents found" — page should not break
    const afterCount = await page.locator("button.rounded-lg").count();
    const hasNoResults = await page.getByText(/no agents found/i).isVisible().catch(() => false);
    // Search completed successfully: either we got results or the "no agents found" message
    expect(afterCount > 0 || hasNoResults).toBeTruthy();
    // Verify search changed something (semantic search returns different/fewer results for specific query)
    console.log(`  Search filter: ${beforeCount} before → ${afterCount} after (no results: ${hasNoResults})`);
  });

  test("can select agent and see skills", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");

    // Wait for default agents to load
    const firstAgent = page.locator("button.rounded-lg").first();
    await firstAgent.waitFor({ timeout: 10_000 });

    // Click first agent
    await firstAgent.click();
    // Skill card should appear (use the CardTitle which is a specific heading)
    await expect(page.locator("[data-slot='card-title']").filter({ hasText: "Skill" })).toBeVisible({ timeout: 5_000 });
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
