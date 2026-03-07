import { test, expect, request } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

const SUMMARIZER_URL = "https://arimatch1-crewhub-agent-summarizer.hf.space";
const TRANSLATOR_URL = "https://arimatch1-crewhub-agent-translator.hf.space";
const API_BASE =
  process.env.E2E_API_BASE || "https://arimatch1-crewhub-staging.hf.space";

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
    await page.getByTestId("detect-url-input").fill(SUMMARIZER_URL);
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

    await page.getByTestId("detect-url-input").fill(SUMMARIZER_URL);
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

    await page.getByTestId("detect-url-input").fill(SUMMARIZER_URL);
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

    await page.getByTestId("detect-url-input").fill(SUMMARIZER_URL);
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

/**
 * Full end-to-end: detect → review → register → success → cleanup.
 *
 * Uses the summarizer agent (owned by the E2E test user). Before running,
 * we delete the existing agent at that endpoint via API to avoid 409.
 * After the test, we look up the newly created agent by endpoint for cleanup.
 */
test.describe("Register Agent Full E2E", () => {
  let createdAgentId: string | null = null;

  // Pre-test: remove existing agent at SUMMARIZER_URL so registration succeeds
  test.beforeAll(async () => {
    const apiKey = process.env.E2E_API_KEY;
    if (!apiKey) throw new Error("E2E_API_KEY required");

    const ctx = await request.newContext({
      baseURL: API_BASE,
      extraHTTPHeaders: { "X-API-Key": apiKey },
    });

    const resp = await ctx.get("/api/v1/agents/", {
      params: { per_page: "100" },
    });
    if (resp.ok()) {
      const body = await resp.json();
      const agents = body.agents || body.items || [];
      for (const agent of agents) {
        if (agent.endpoint === SUMMARIZER_URL) {
          await ctx.delete(`/api/v1/agents/${agent.id}/permanent`);
        }
      }
    }
    await ctx.dispose();
  });

  // Post-test: clean up via API (find by endpoint)
  test.afterAll(async () => {
    const apiKey = process.env.E2E_API_KEY;
    if (!apiKey) return;

    const ctx = await request.newContext({
      baseURL: API_BASE,
      extraHTTPHeaders: { "X-API-Key": apiKey },
    });

    // If we captured the ID, delete directly
    if (createdAgentId) {
      await ctx.delete(`/api/v1/agents/${createdAgentId}/permanent`);
    }
    await ctx.dispose();
  });

  test("detect → register → success page", async ({ page }) => {
    await loginWithApiKey(page);
    await page.goto("/register-agent");

    // Step 1: Paste summarizer URL and detect
    await page.getByTestId("detect-url-input").fill(SUMMARIZER_URL);
    await page.getByTestId("detect-button").click();

    // Step 2: Review step with auto-filled data
    await expect(
      page.getByRole("heading", { name: "Review & Register" })
    ).toBeVisible({ timeout: 30_000 });

    const nameInput = page.getByTestId("review-name");
    await expect(nameInput).toHaveValue(/.+/);

    // Click Register
    const registerBtn = page.getByTestId("register-button");
    await expect(registerBtn).toBeEnabled({ timeout: 5_000 });
    await registerBtn.click();

    // Step 3: Success page
    await expect(
      page.getByRole("heading", { name: "Agent Registered!" })
    ).toBeVisible({ timeout: 30_000 });

    await expect(page.getByText(/now live on the marketplace/i)).toBeVisible();
    await expect(page.getByTestId("view-agent-button")).toBeVisible();

    // Find the newly created agent by endpoint to get its ID for cleanup
    const apiKey = process.env.E2E_API_KEY || "";
    const ctx = await request.newContext({
      baseURL: API_BASE,
      extraHTTPHeaders: { "X-API-Key": apiKey },
    });
    const resp = await ctx.get("/api/v1/agents/", {
      params: { per_page: "100" },
    });
    if (resp.ok()) {
      const body = await resp.json();
      const agents = body.agents || body.items || [];
      const match = agents.find(
        (a: { endpoint: string }) => a.endpoint === SUMMARIZER_URL
      );
      if (match) createdAgentId = match.id;
    }
    await ctx.dispose();

    expect(createdAgentId).toBeTruthy();
  });
});
