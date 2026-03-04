import { Page } from "@playwright/test";

/**
 * Set up auth in the browser by injecting an API key into localStorage.
 * Uses the __playwright_auth__ bypass flag so Firebase onAuthStateChanged
 * doesn't clear the token.
 */
export async function loginWithApiKey(page: Page, apiKey?: string) {
  const key = apiKey || process.env.E2E_API_KEY || "";
  if (!key) {
    throw new Error("E2E_API_KEY environment variable is required");
  }

  await page.goto("/");
  await page.evaluate(
    ({ token }) => {
      localStorage.setItem("auth_token", token);
      localStorage.setItem("__playwright_auth__", "1");
    },
    { token: key }
  );
  // Reload so the auth context picks up the token
  await page.reload();
  await page.waitForLoadState("networkidle");
}
