import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Dashboard Agent Analytics", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("analytics section visible when user has agents", async ({ page }) => {
    await page.goto("/dashboard/agents");

    // Wait for agents to load — either the analytics section or the empty state
    const analytics = page.getByTestId("analytics-section");
    const empty = page.getByText(/no agents registered/i);

    await expect(analytics.or(empty).first()).toBeVisible({ timeout: 15_000 });

    // If analytics section is visible, verify aggregate stats
    if (await analytics.isVisible()) {
      const stats = page.getByTestId("analytics-aggregate-stats");
      await expect(stats).toBeVisible();
      await expect(stats.getByText("Total Tasks (all agents)")).toBeVisible();
      await expect(stats.getByText("Avg Success Rate")).toBeVisible();
      await expect(stats.getByText("Avg Latency")).toBeVisible();
      await expect(stats.getByText(/Earnings/)).toBeVisible();
    }
  });

  test("per-agent rows show metrics and sparklines", async ({ page }) => {
    await page.goto("/dashboard/agents");

    const analytics = page.getByTestId("analytics-section");
    // Skip if no agents
    if (!(await analytics.isVisible({ timeout: 10_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    // Check per-agent rows exist
    const rows = page.getByTestId("analytics-agent-row");
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);

    // First row should have metrics
    const firstRow = rows.first();
    await expect(firstRow.getByText("tasks")).toBeVisible();
    await expect(firstRow.getByText("success")).toBeVisible();
    await expect(firstRow.getByText("score")).toBeVisible();
  });

  test("agent name links to detail page", async ({ page }) => {
    await page.goto("/dashboard/agents");

    const analytics = page.getByTestId("analytics-section");
    if (!(await analytics.isVisible({ timeout: 10_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    // First agent row should have a link
    const firstRow = page.getByTestId("analytics-agent-row").first();
    const link = firstRow.locator("a");
    await expect(link).toBeVisible();

    const href = await link.getAttribute("href");
    expect(href).toMatch(/\/agents\/.+/);
  });
});
