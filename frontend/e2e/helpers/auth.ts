import { Page } from "@playwright/test";

/**
 * Set up auth in the browser by injecting an API key into localStorage
 * and setting the __auth_token cookie so Next.js middleware allows
 * access to /dashboard/* routes.
 */
export async function loginWithApiKey(page: Page, apiKey?: string) {
  const key = apiKey || process.env.E2E_API_KEY || "";
  if (!key) {
    throw new Error("E2E_API_KEY environment variable is required");
  }

  // Navigate to a public page first to establish the domain
  await page.goto("/agents");
  await page.waitForLoadState("domcontentloaded");

  // Set localStorage tokens
  await page.evaluate(
    ({ token }) => {
      localStorage.setItem("auth_token", token);
      localStorage.setItem("__playwright_auth__", "1");
    },
    { token: key }
  );

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

  // Reload so the auth context picks up the token
  await page.reload();
  await page.waitForLoadState("networkidle");
}
