import { Page } from "@playwright/test";

/**
 * Set up auth in the browser by injecting an API key into localStorage
 * and setting the __auth_token cookie so Next.js middleware allows
 * access to /dashboard/* routes.
 *
 * Uses addInitScript to inject the token before any JS runs, avoiding
 * race conditions between page load and localStorage setup.
 */
export async function loginWithApiKey(page: Page, apiKey?: string) {
  const key = apiKey || process.env.E2E_API_KEY || "";
  if (!key) {
    throw new Error("E2E_API_KEY environment variable is required");
  }

  // Inject auth token into localStorage before any page JS executes.
  // This ensures the auth context sees the token on its first render.
  await page.addInitScript(
    ({ token }) => {
      localStorage.setItem("auth_token", token);
      localStorage.setItem("__playwright_auth__", "1");
    },
    { token: key }
  );

  // Navigate to a public page to establish the domain and set the cookie
  await page.goto("/agents");
  await page.waitForLoadState("domcontentloaded");

  // Set the auth cookie so Next.js middleware allows /dashboard/* routes
  const url = new URL(page.url());
  await page.context().addCookies([
    {
      name: "__auth_token",
      value: key,
      domain: url.hostname,
      path: "/",
      sameSite: "Strict",
    },
  ]);

  // Wait for auth to fully resolve — the "Sign In" button should disappear
  // once the auth context has loaded the user profile
  await page.getByText("Sign In").waitFor({ state: "hidden", timeout: 30_000 });
}
