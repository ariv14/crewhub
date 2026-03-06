import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Developer Onboarding", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("fork screen renders two path cards", async ({ page }) => {
    await page.goto("/onboarding");
    await expect(page.getByTestId("fork-use-agents")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByTestId("fork-build-agents")).toBeVisible();
    await expect(page.getByText("Use Agents")).toBeVisible();
    await expect(page.getByText("Build Agents")).toBeVisible();
  });

  test("'Use Agents' shows existing onboarding steps", async ({ page }) => {
    await page.goto("/onboarding");
    await page.getByTestId("fork-use-agents").click();
    // Should see the first step of the existing wizard (Welcome)
    await expect(page.getByText("Welcome")).toBeVisible({ timeout: 5_000 });
  });

  test("'Build Agents' shows developer onboarding", async ({ page }) => {
    await page.goto("/onboarding");
    await page.getByTestId("fork-build-agents").click();
    // Should see the URL input and detect button
    await expect(page.getByTestId("detect-url-input")).toBeVisible({
      timeout: 5_000,
    });
    await expect(page.getByTestId("detect-button")).toBeVisible();
    await expect(page.getByText("Paste URL")).toBeVisible();
  });

  test("back button returns to fork screen", async ({ page }) => {
    await page.goto("/onboarding");
    await page.getByTestId("fork-build-agents").click();
    await expect(page.getByTestId("detect-url-input")).toBeVisible({
      timeout: 5_000,
    });
    // Click back
    await page.getByRole("button", { name: /back/i }).click();
    // Should be back at fork screen
    await expect(page.getByTestId("fork-use-agents")).toBeVisible({
      timeout: 5_000,
    });
  });

  test("detect with invalid URL shows error", async ({ page }) => {
    await page.goto("/onboarding");
    await page.getByTestId("fork-build-agents").click();
    const input = page.getByTestId("detect-url-input");
    await input.waitFor({ timeout: 5_000 });
    await input.fill("https://nonexistent-agent-endpoint-12345.example.com");
    await page.getByTestId("detect-button").click();
    // Should show an error (either toast or inline)
    await expect(
      page.locator("[class*='destructive'], [data-sonner-toast]").first()
    ).toBeVisible({ timeout: 15_000 });
  });

  test("detect button is disabled when URL is empty", async ({ page }) => {
    await page.goto("/onboarding");
    await page.getByTestId("fork-build-agents").click();
    await expect(page.getByTestId("detect-url-input")).toBeVisible({
      timeout: 5_000,
    });
    await expect(page.getByTestId("detect-button")).toBeDisabled();
  });
});
