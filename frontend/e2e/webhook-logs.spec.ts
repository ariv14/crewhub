import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

// Known agent owned by test user on staging
const AGENT_ID = "d2d390f6-dd93-4334-9147-b8e01fcf58e6"; // AI Agency: Testing

test.describe("Webhook Logs Viewer", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("webhook logs section visible on agent settings page", async ({
    page,
  }) => {
    await page.goto(`/dashboard/agents/${AGENT_ID}/`);

    // Wait for the settings page to load
    await expect(page.getByText("Agent Settings")).toBeVisible({
      timeout: 15_000,
    });

    // Webhook logs section should be visible
    const viewer = page.getByTestId("webhook-logs-viewer");
    await expect(viewer).toBeVisible({ timeout: 10_000 });
    await expect(viewer.getByText("Webhook Logs")).toBeVisible();
    await expect(
      viewer.getByText(/A2A communication history/)
    ).toBeVisible();
  });

  test("webhook logs show filters", async ({ page }) => {
    await page.goto(`/dashboard/agents/${AGENT_ID}/`);
    await expect(page.getByText("Agent Settings")).toBeVisible({
      timeout: 15_000,
    });

    const filters = page.getByTestId("webhook-filters");
    await expect(filters).toBeVisible({ timeout: 10_000 });

    // Direction filters
    await expect(filters.getByText("Inbound")).toBeVisible();
    await expect(filters.getByText("Outbound")).toBeVisible();

    // Status filters
    await expect(filters.getByText("Success")).toBeVisible();
    await expect(filters.getByText("Failed")).toBeVisible();
  });

  test("webhook logs show entries or empty state", async ({ page }) => {
    await page.goto(`/dashboard/agents/${AGENT_ID}/`);
    await expect(page.getByText("Agent Settings")).toBeVisible({
      timeout: 15_000,
    });

    const viewer = page.getByTestId("webhook-logs-viewer");

    // Either log rows or "No webhook logs yet" empty state
    const logRow = viewer.getByTestId("webhook-log-row").first();
    const emptyState = viewer.getByText("No webhook logs yet");

    await expect(logRow.or(emptyState)).toBeVisible({ timeout: 10_000 });

    if (await logRow.isVisible()) {
      // If we have logs, verify they show expected content
      const firstRow = logRow;
      // Should show a method like tasks/send or tasks/statusUpdate
      await expect(firstRow.getByText(/tasks\//)).toBeVisible();
    }
  });
});
