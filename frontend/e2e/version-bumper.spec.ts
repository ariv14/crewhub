import { test, expect } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

// Known agent owned by test user on staging
const AGENT_ID = "d2d390f6-dd93-4334-9147-b8e01fcf58e6"; // AI Agency: Testing

test.describe("Version Bumper", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  test("version bumper renders with bump buttons on agent settings", async ({
    page,
  }) => {
    await page.goto(`/dashboard/agents/${AGENT_ID}/`);
    await expect(page.getByText("Agent Settings")).toBeVisible({
      timeout: 15_000,
    });

    const bumper = page.getByTestId("version-bumper");
    await expect(bumper).toBeVisible({ timeout: 10_000 });

    // Should show the version input with a semver value
    const input = bumper.locator("input");
    const value = await input.inputValue();
    expect(value).toMatch(/^\d+\.\d+\.\d+$/);

    // Bump buttons should be visible for valid semver
    const buttons = page.getByTestId("version-bump-buttons");
    await expect(buttons).toBeVisible();
    await expect(buttons.getByText("Patch")).toBeVisible();
    await expect(buttons.getByText("Minor")).toBeVisible();
    await expect(buttons.getByText("Major")).toBeVisible();
  });

  test("patch button increments patch version", async ({ page }) => {
    await page.goto(`/dashboard/agents/${AGENT_ID}/`);
    await expect(page.getByText("Agent Settings")).toBeVisible({
      timeout: 15_000,
    });

    const bumper = page.getByTestId("version-bumper");
    const input = bumper.locator("input");
    const before = await input.inputValue();

    // Parse current version
    const [major, minor, patch] = before.split(".").map(Number);

    // Click patch
    await page.getByTestId("version-bump-buttons").getByText("Patch").click();

    const after = await input.inputValue();
    expect(after).toBe(`${major}.${minor}.${patch + 1}`);
  });

  test("minor button increments minor and resets patch", async ({ page }) => {
    await page.goto(`/dashboard/agents/${AGENT_ID}/`);
    await expect(page.getByText("Agent Settings")).toBeVisible({
      timeout: 15_000,
    });

    const bumper = page.getByTestId("version-bumper");
    const input = bumper.locator("input");
    const before = await input.inputValue();
    const [major, minor] = before.split(".").map(Number);

    await page.getByTestId("version-bump-buttons").getByText("Minor").click();

    const after = await input.inputValue();
    expect(after).toBe(`${major}.${minor + 1}.0`);
  });

  test("major button increments major and resets minor+patch", async ({
    page,
  }) => {
    await page.goto(`/dashboard/agents/${AGENT_ID}/`);
    await expect(page.getByText("Agent Settings")).toBeVisible({
      timeout: 15_000,
    });

    const bumper = page.getByTestId("version-bumper");
    const input = bumper.locator("input");
    const before = await input.inputValue();
    const [major] = before.split(".").map(Number);

    await page.getByTestId("version-bump-buttons").getByText("Major").click();

    const after = await input.inputValue();
    expect(after).toBe(`${major + 1}.0.0`);
  });

  test("non-semver input hides bump buttons and shows warning", async ({
    page,
  }) => {
    await page.goto(`/dashboard/agents/${AGENT_ID}/`);
    await expect(page.getByText("Agent Settings")).toBeVisible({
      timeout: 15_000,
    });

    const bumper = page.getByTestId("version-bumper");
    const input = bumper.locator("input");

    // Clear and type non-semver
    await input.clear();
    await input.fill("latest");

    // Bump buttons should disappear
    await expect(page.getByTestId("version-bump-buttons")).not.toBeVisible();

    // Warning should appear
    await expect(bumper.getByText(/Not a semver format/)).toBeVisible();
  });
});
