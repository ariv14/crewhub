import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

test.describe("Register Agent Flow", () => {
  test("landing page shows Use Agents and Build Agents cards", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Use Agents" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Build Agents" })).toBeVisible();
    await expect(page.getByText("start earning")).toBeVisible();
  });

  test("Build Agents card navigates to /register-agent", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /build agents/i }).click();
    await page.waitForURL(/\/register-agent/, { timeout: 10_000 });
    await expect(
      page.getByRole("heading", { name: "Register Your Agent" })
    ).toBeVisible();
  });

  test("register page shows 3-step flow", async ({ page }) => {
    await page.goto("/register-agent");
    await expect(page.getByText("Paste URL")).toBeVisible();
    await expect(page.getByText("Review & Register")).toBeVisible();
    await expect(page.getByText("Live")).toBeVisible();
    await expect(page.getByText(".well-known/agent-card.json")).toBeVisible();
  });

  test("detect button is disabled without URL", async ({ page }) => {
    await page.goto("/register-agent");
    const detectBtn = page.getByTestId("detect-button");
    await expect(detectBtn).toBeDisabled();
  });

  test("detect agent auto-fills review step", async ({ page }) => {
    await page.goto("/register-agent");

    // Paste URL and detect
    await page.getByTestId("detect-url-input").fill(
      "https://arimatch1-crewhub-agent-summarizer.hf.space"
    );
    await page.getByTestId("detect-button").click();

    // Wait for review step to appear (detection calls staging backend)
    await expect(
      page.getByRole("heading", { name: "Review & Register" })
    ).toBeVisible({ timeout: 30_000 });

    // Verify auto-filled fields
    const nameInput = page.getByTestId("review-name");
    await expect(nameInput).toHaveValue(/summarizer/i);

    // Skills badges should be visible
    await expect(page.getByText("Detected Skills")).toBeVisible();

    // Pricing section should be visible
    await expect(page.getByText("Pricing")).toBeVisible();
    await expect(page.getByText("Credits/Task")).toBeVisible();
  });

  test("unauthenticated user sees sign-in gate", async ({ page }) => {
    await page.goto("/register-agent");

    await page.getByTestId("detect-url-input").fill(
      "https://arimatch1-crewhub-agent-summarizer.hf.space"
    );
    await page.getByTestId("detect-button").click();

    await expect(
      page.getByRole("heading", { name: "Review & Register" })
    ).toBeVisible({ timeout: 30_000 });

    // Without auth, sign-in gate should appear
    await expect(page.getByText("Sign in to register your agent")).toBeVisible();
    // Register button should be disabled
    await expect(page.getByTestId("register-button")).toBeDisabled();
  });

  test("authenticated user can reach register button", async ({ page }) => {
    await loginWithApiKey(page);
    await page.goto("/register-agent");

    await page.getByTestId("detect-url-input").fill(
      "https://arimatch1-crewhub-agent-summarizer.hf.space"
    );
    await page.getByTestId("detect-button").click();

    await expect(
      page.getByRole("heading", { name: "Review & Register" })
    ).toBeVisible({ timeout: 30_000 });

    // Sign-in gate should NOT appear
    await expect(page.getByText("Sign in to register your agent")).toBeHidden();

    // Register button should be enabled (name is auto-filled)
    await expect(page.getByTestId("register-button")).toBeEnabled();
  });

  test("back button returns to paste step", async ({ page }) => {
    await page.goto("/register-agent");

    await page.getByTestId("detect-url-input").fill(
      "https://arimatch1-crewhub-agent-summarizer.hf.space"
    );
    await page.getByTestId("detect-button").click();

    await expect(
      page.getByRole("heading", { name: "Review & Register" })
    ).toBeVisible({ timeout: 30_000 });

    await page.getByRole("button", { name: "Back" }).click();

    // Should be back on paste step
    await expect(
      page.getByRole("heading", { name: "Agent Endpoint" })
    ).toBeVisible();
  });

  test("invalid URL shows error", async ({ page }) => {
    await page.goto("/register-agent");

    await page.getByTestId("detect-url-input").fill("https://nonexistent-agent.invalid");
    await page.getByTestId("detect-button").click();

    // Should show an error (toast or inline)
    await expect(
      page.getByText(/could not reach|failed|error|timed out/i).first()
    ).toBeVisible({ timeout: 15_000 });
  });
});
