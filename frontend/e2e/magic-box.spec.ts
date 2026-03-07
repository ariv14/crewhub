import { test, expect } from "@playwright/test";

test.describe("Magic Box Onboarding", () => {
  test("landing page shows magic box with input and starters", async ({
    page,
  }) => {
    await page.goto("/");

    const magicBox = page.getByTestId("magic-box");
    await expect(magicBox).toBeVisible({ timeout: 10_000 });

    // Input visible with placeholder
    const input = page.getByTestId("magic-box-input");
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute(
      "placeholder",
      "What do you need help with?"
    );

    // Find Agent button visible
    await expect(page.getByRole("button", { name: "Find Agent" })).toBeVisible();

    // Conversation starters visible
    const starters = page.getByTestId("magic-box-starters");
    await expect(starters).toBeVisible();
    await expect(starters.locator("button").first()).toBeVisible();
  });

  test("clicking a starter populates the input", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("magic-box")).toBeVisible({ timeout: 10_000 });

    const starter = page.getByTestId("magic-box-starters").locator("button").first();
    const starterText = await starter.textContent();
    await starter.click();

    const input = page.getByTestId("magic-box-input");
    await expect(input).toHaveValue(starterText!);
  });

  test("Find Agent button is disabled for short queries", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("magic-box")).toBeVisible({ timeout: 10_000 });

    const btn = page.getByRole("button", { name: "Find Agent" });
    await expect(btn).toBeDisabled();

    // Type short text
    await page.getByTestId("magic-box-input").fill("hi");
    await expect(btn).toBeDisabled();

    // Type longer text
    await page.getByTestId("magic-box-input").fill("translate my document");
    await expect(btn).toBeEnabled();
  });

  test("search returns suggestion cards or empty state", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("magic-box")).toBeVisible({ timeout: 10_000 });

    await page.getByTestId("magic-box-input").fill("help me test my API endpoints");
    await page.getByRole("button", { name: "Find Agent" }).click();

    // Wait for either results or empty state
    const results = page.getByTestId("magic-box-results");
    const empty = page.getByTestId("magic-box-empty");
    await expect(results.or(empty)).toBeVisible({ timeout: 15_000 });

    if (await results.isVisible()) {
      // Should have at least one suggestion card
      const card = page.getByTestId("suggestion-card").first();
      await expect(card).toBeVisible();

      // Card should link to task creation
      const href = await card.getAttribute("href");
      expect(href).toContain("/dashboard/tasks/new/");
    }
  });

  test("developer path links are visible", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("magic-box")).toBeVisible({ timeout: 10_000 });

    await expect(page.getByText("Browse all agents →")).toBeVisible();
    await expect(page.getByText("I build agents")).toBeVisible();
  });
});
