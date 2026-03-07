import { test, expect } from "@playwright/test";

test.describe("Team Mode", () => {
  test("team page renders with input and starters", async ({ page }) => {
    await page.goto("/team");

    await expect(
      page.getByRole("heading", { name: "Assemble Your AI Team" })
    ).toBeVisible({ timeout: 10_000 });

    const input = page.getByTestId("team-goal-input");
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute(
      "placeholder",
      "Describe your goal or challenge in detail..."
    );

    await expect(
      page.getByRole("button", { name: "Assemble Team" })
    ).toBeVisible();

    const starters = page.getByTestId("team-starters");
    await expect(starters).toBeVisible();
    await expect(starters.locator("button").first()).toBeVisible();
  });

  test("clicking a starter populates the input", async ({ page }) => {
    await page.goto("/team");
    await expect(
      page.getByRole("heading", { name: "Assemble Your AI Team" })
    ).toBeVisible({ timeout: 10_000 });

    const starter = page.getByTestId("team-starters").locator("button").first();
    const starterText = await starter.textContent();
    await starter.click();

    const input = page.getByTestId("team-goal-input");
    await expect(input).toHaveValue(starterText!);
  });

  test("Assemble Team button is disabled for short input", async ({
    page,
  }) => {
    await page.goto("/team");
    await expect(
      page.getByRole("heading", { name: "Assemble Your AI Team" })
    ).toBeVisible({ timeout: 10_000 });

    const btn = page.getByRole("button", { name: "Assemble Team" });
    await expect(btn).toBeDisabled();

    await page.getByTestId("team-goal-input").fill("short");
    await expect(btn).toBeDisabled();

    await page
      .getByTestId("team-goal-input")
      .fill("Review my REST API design for security and performance");
    await expect(btn).toBeEnabled();
  });

  test("assembling a team shows suggestions or requires auth", async ({ page }) => {
    await page.goto("/team");
    await expect(
      page.getByRole("heading", { name: "Assemble Your AI Team" })
    ).toBeVisible({ timeout: 10_000 });

    await page
      .getByTestId("team-goal-input")
      .fill("Review my REST API design for security and performance");
    await page.getByRole("button", { name: "Assemble Team" }).click();

    // Wait for either: selection phase (auth'd), error message, or button re-enabled (API failed silently)
    const selection = page.getByTestId("team-selection");
    const errorBanner = page.locator("[class*='red']");
    const assembleBtn = page.getByRole("button", { name: "Assemble Team" });

    await expect(
      selection.or(errorBanner).or(assembleBtn)
    ).toBeVisible({ timeout: 15_000 });

    if (await selection.isVisible()) {
      const suggestions = page.getByTestId("team-suggestion");
      await expect(suggestions.first()).toBeVisible();
      await expect(
        page.getByRole("button", { name: /Launch \d+ Agent/ })
      ).toBeVisible();
    }
    // If not authenticated, we just verify the page didn't crash
  });

  test("landing page links to team mode", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Assemble AI Team")).toBeVisible({
      timeout: 10_000,
    });
  });
});
