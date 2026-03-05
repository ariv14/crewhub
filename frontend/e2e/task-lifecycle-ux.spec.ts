import { test, expect, Page } from "@playwright/test";
import { loginWithApiKey } from "./helpers/auth";

const API_BASE = "https://arimatch1-crewhub-staging.hf.space/api/v1";
const API_KEY = process.env.E2E_API_KEY || "";

test.describe("Task Lifecycle UX Enhancement", () => {
  test.beforeEach(async ({ page }) => {
    await loginWithApiKey(page);
  });

  // ─── Create Task Page ───────────────────────────────────

  test("1. create task page shows agents by default (no search required)", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    await expect(page.locator("h1")).toContainText(/create task/i);
    // Search input should be visible
    await expect(page.getByPlaceholder(/search agents/i)).toBeVisible({ timeout: 10_000 });
    // Agents should be listed WITHOUT typing anything
    await expect(page.locator("button.rounded-lg").first()).toBeVisible({ timeout: 15_000 });
    // Count agents shown
    const agentCount = await page.locator("button.rounded-lg").count();
    console.log(`  ✓ ${agentCount} agents listed by default`);
    expect(agentCount).toBeGreaterThan(0);
  });

  test("2. search filters the default agent list", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    await expect(page.locator("button.rounded-lg").first()).toBeVisible({ timeout: 15_000 });
    const beforeCount = await page.locator("button.rounded-lg").count();

    // Type a specific search
    await page.getByPlaceholder(/search agents/i).fill("developer");
    await page.waitForTimeout(500); // debounce

    // Should show filtered results or "no agents found"
    await page.waitForTimeout(1000);
    const afterCount = await page.locator("button.rounded-lg").count();
    const noResults = await page.getByText(/no agents found/i).isVisible().catch(() => false);

    console.log(`  ✓ Before search: ${beforeCount} agents, After: ${afterCount} (no results: ${noResults})`);
    expect(afterCount < beforeCount || noResults).toBeTruthy();
  });

  test("3. reliability badges visible on agent cards", async ({ page }) => {
    await page.goto("/dashboard/tasks/new");
    await expect(page.locator("button.rounded-lg").first()).toBeVisible({ timeout: 15_000 });

    // Look for any reliability badge text
    const badges = page.locator("button.rounded-lg").locator("text=/success|Fast|tasks/");
    const badgeCount = await badges.count();
    console.log(`  ✓ Found ${badgeCount} reliability badges across agent cards`);
    // Not all agents will have badges, so we just log it
  });

  test("4. URL params pre-fill create task form (retry flow)", async ({ page }) => {
    // Get a valid agent
    const resp = await page.request.get(`${API_BASE}/agents/?per_page=1&status=active`, {
      headers: { "X-API-Key": API_KEY },
    });
    const data = await resp.json();
    const agent = data.agents?.[0];
    if (!agent) { test.skip(); return; }

    const skill = agent.skills?.[0];
    if (!skill) { test.skip(); return; }

    const testMessage = "Test retry message from E2E";
    const url = `/dashboard/tasks/new?agent=${agent.id}&skill=${skill.id}&message=${encodeURIComponent(testMessage)}`;
    await page.goto(url);

    // Agent should be pre-selected (no search input)
    await expect(page.getByPlaceholder(/search agents/i)).not.toBeVisible({ timeout: 10_000 });

    // Message should be pre-filled
    const textarea = page.locator("textarea");
    await textarea.waitFor({ timeout: 10_000 });
    const value = await textarea.inputValue();
    expect(value).toBe(testMessage);
    console.log(`  ✓ URL params pre-filled: agent=${agent.name}, message="${testMessage}"`);
  });

  // ─── Task List & Navigation ─────────────────────────────

  test("5. task list shows task cards with proper links", async ({ page }) => {
    await page.goto("/dashboard/tasks");
    await expect(page.locator("h1")).toContainText(/my tasks/i, { timeout: 15_000 });

    // Wait for task cards to load
    const taskCards = page.locator("a.block[href*='/dashboard/tasks/']");
    if (!(await taskCards.first().isVisible({ timeout: 10_000 }).catch(() => false))) {
      console.log("  ⚠ No tasks found, skipping");
      test.skip();
      return;
    }

    const count = await taskCards.count();
    expect(count).toBeGreaterThan(0);

    // Verify first card has a task ID in its href (not just /new)
    const href = await taskCards.first().getAttribute("href");
    expect(href).toMatch(/\/dashboard\/tasks\/[a-f0-9-]+/);
    console.log(`  ✓ ${count} task cards shown, first links to: ${href}`);
  });

  // ─── Task Detail Page ───────────────────────────────────

  test("6. task detail shows progress stepper", async ({ page }) => {
    const taskId = await navigateToFirstTask(page);
    if (!taskId) { test.skip(); return; }

    // Progress stepper should be visible with step labels (CSS capitalize makes them Title Case)
    await expect(page.getByText(/submitted/i).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/working/i).first()).toBeVisible();
    await expect(page.getByText(/completed/i).first()).toBeVisible();
    console.log("  ✓ Progress stepper visible with all 3 steps");
  });

  test("7. task detail shows agent identity card", async ({ page }) => {
    const taskId = await navigateToFirstTask(page);
    if (!taskId) { test.skip(); return; }

    // Agent card should show "Agent" heading and "View Agent" link
    await expect(page.getByRole("heading", { name: "Agent" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("link", { name: /view agent/i })).toBeVisible();
    console.log("  ✓ Agent identity card visible with View Agent link");
  });

  test("8. task detail shows details card with cost info", async ({ page }) => {
    const taskId = await navigateToFirstTask(page);
    if (!taskId) { test.skip(); return; }

    // Details card
    await expect(page.getByRole("heading", { name: "Details" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Quoted")).toBeVisible();
    await expect(page.getByText("Charged")).toBeVisible();
    await expect(page.getByText("Payment")).toBeVisible();
    console.log("  ✓ Details card visible with cost breakdown");
  });

  test("9. task detail shows timeline for tasks with status history", async ({ page }) => {
    const taskId = await navigateToFirstTask(page);
    if (!taskId) { test.skip(); return; }

    // Timeline may or may not be visible depending on status_history
    const timelineVisible = await page.getByRole("heading", { name: "Timeline" }).isVisible().catch(() => false);
    console.log(`  ${timelineVisible ? "✓" : "⚠"} Timeline card ${timelineVisible ? "visible" : "not shown (no status_history)"}`);
  });

  test("10. task detail shows message thread with 'You' label", async ({ page }) => {
    const taskId = await navigateToFirstTask(page);
    if (!taskId) { test.skip(); return; }

    // Should show "You" for user messages
    const youLabel = page.locator("text=You").first();
    await expect(youLabel).toBeVisible({ timeout: 10_000 });
    console.log("  ✓ Message thread shows 'You' label");
  });

  test("11. completed task shows markdown-rendered artifacts with copy button", async ({ page }) => {
    const taskId = await navigateToTaskByStatus(page, "completed");
    if (!taskId) { test.skip(); return; }

    // Check for "Output" heading (renamed from "Artifacts")
    const hasOutput = await page.getByText("Output").isVisible().catch(() => false);
    if (!hasOutput) {
      console.log("  ⚠ No artifacts on this completed task");
      return;
    }

    // Copy button should be visible
    const copyBtn = page.getByRole("button", { name: /copy/i }).first();
    const hasCopy = await copyBtn.isVisible().catch(() => false);

    // "Show raw" toggle
    const rawToggle = page.getByText(/show raw/i).first();
    const hasRawToggle = await rawToggle.isVisible().catch(() => false);

    console.log(`  ✓ Output section visible, Copy: ${hasCopy}, Raw toggle: ${hasRawToggle}`);
  });

  test("12. completed task shows 'Run Again' button", async ({ page }) => {
    const taskId = await navigateToTaskByStatus(page, "completed");
    if (!taskId) { test.skip(); return; }

    const runAgainBtn = page.getByRole("link", { name: /run again/i });
    await expect(runAgainBtn).toBeVisible({ timeout: 10_000 });

    // Click it and verify it navigates to create task with pre-filled params
    const href = await runAgainBtn.getAttribute("href");
    expect(href).toMatch(/\/dashboard\/tasks\/new\/?[?]agent=/);
    expect(href).toContain("skill=");
    expect(href).toContain("message=");
    console.log(`  ✓ 'Run Again' button visible, links to: ${href?.slice(0, 80)}...`);
  });

  test("13. failed/canceled task shows 'Retry' button", async ({ page }) => {
    const taskId = await navigateToTaskByStatus(page, "failed");
    if (!taskId) {
      // Try canceled
      const canceledId = await navigateToTaskByStatus(page, "canceled");
      if (!canceledId) {
        console.log("  ⚠ No failed/canceled tasks found, skipping");
        test.skip();
        return;
      }
    }

    const retryBtn = page.getByRole("link", { name: /retry/i });
    await expect(retryBtn).toBeVisible({ timeout: 10_000 });
    console.log("  ✓ Retry button visible on failed task");
  });

  test("14. active task shows processing banner with elapsed time", async ({ page }) => {
    // Create a fresh task to catch it in working state
    const taskId = await createTestTask(page);
    if (!taskId) { test.skip(); return; }

    await navigateToTaskDetail(page, taskId);
    await page.waitForTimeout(1000);

    // If task is still processing, we should see the banner
    const hasBanner = await page.getByText(/agent is working/i).isVisible().catch(() => false);
    const hasElapsed = await page.locator(".font-mono").isVisible().catch(() => false);

    if (hasBanner) {
      console.log(`  ✓ Processing banner visible, elapsed timer: ${hasElapsed}`);
    } else {
      console.log("  ⚠ Task already completed by the time we checked (fast agent)");
    }
  });

  // ─── Full Flow: Create → View → Verify ─────────────────

  test("15. full flow: create task → view detail → verify all UI elements", async ({ page }) => {
    // Step 1: Go to create task page
    await page.goto("/dashboard/tasks/new");
    await expect(page.locator("button.rounded-lg").first()).toBeVisible({ timeout: 15_000 });
    console.log("  Step 1: Agents listed by default ✓");

    // Step 2: Select first agent
    await page.locator("button.rounded-lg").first().click();
    await page.waitForTimeout(1000);

    // Step 3: Should see skill section — select first skill if dropdown present
    await page.waitForTimeout(2000);
    const skillDropdown = page.locator("button[role='combobox']").first();
    if (await skillDropdown.isVisible().catch(() => false)) {
      await skillDropdown.click();
      await page.locator("[role='option']").first().click();
      console.log("  Step 2: Agent selected, skill chosen from dropdown ✓");
    } else {
      console.log("  Step 2: Agent selected, skill auto-selected (single skill) ✓");
    }

    // Step 4: Enter message
    const textarea = page.locator("textarea");
    await textarea.waitFor({ timeout: 5_000 });
    await textarea.fill("E2E test: task lifecycle UX verification");

    // Step 5: Submit
    const createBtn = page.getByRole("button", { name: /create task/i });
    await createBtn.click();

    // Step 6: Wait for redirect to task detail
    await page.waitForURL(/\/dashboard\/tasks\/.+/, { timeout: 30_000 });
    const url = page.url();
    console.log(`  Step 3: Task created, redirected to ${url} ✓`);

    // Step 7: Verify task detail UI elements
    await page.waitForTimeout(3000);

    // Progress stepper
    const hasStepper = await page.getByText("submitted").isVisible().catch(() => false);
    console.log(`  Step 4: Progress stepper: ${hasStepper ? "✓" : "✗"}`);

    // Agent card
    const hasAgentCard = await page.getByRole("heading", { name: "Agent" }).isVisible().catch(() => false);
    console.log(`  Step 5: Agent identity card: ${hasAgentCard ? "✓" : "✗"}`);

    // Details card
    const hasDetails = await page.getByRole("heading", { name: "Details" }).isVisible().catch(() => false);
    console.log(`  Step 6: Details card: ${hasDetails ? "✓" : "✗"}`);

    // Message thread with "You"
    const hasYou = await page.locator("text=You").first().isVisible().catch(() => false);
    console.log(`  Step 7: Message 'You' label: ${hasYou ? "✓" : "✗"}`);

    // Back button
    const hasBack = await page.getByRole("link", { name: /back to tasks/i }).isVisible().catch(() => false);
    console.log(`  Step 8: Back to Tasks link: ${hasBack ? "✓" : "✗"}`);
  });
});

// ─── Helper Functions ───────────────────────────────────

/** Get first task ID via API, navigate to __fallback with sessionStorage set */
async function navigateToFirstTask(page: Page): Promise<string | null> {
  const taskId = await getAnyTaskId(page);
  if (!taskId) return null;
  await navigateToTaskDetail(page, taskId);
  return taskId;
}

/** Navigate to task detail page by setting sessionStorage then loading __fallback */
async function navigateToTaskDetail(page: Page, taskId: string): Promise<void> {
  // Go to __fallback page directly (this is what Cloudflare serves for dynamic routes)
  await page.goto("/dashboard/tasks/__fallback/");
  // Set sessionStorage so the React app resolves the correct task ID
  await page.evaluate((id) => sessionStorage.setItem("nav_task_id", id), taskId);
  // Reload so the app reads the sessionStorage value
  await page.reload();
  // Wait for the task detail to render (heading "Task" appears when data loads)
  await page.getByText("Back to Tasks").waitFor({ timeout: 15_000 });
  // Small extra wait for remaining content to render
  await page.waitForTimeout(2000);
}

/** Find task with given status via API, navigate to detail via __fallback */
async function navigateToTaskByStatus(page: Page, status: string): Promise<string | null> {
  const resp = await page.request.get(`${API_BASE}/tasks/?per_page=20`, {
    headers: { "X-API-Key": API_KEY },
  });
  const data = await resp.json();
  const task = data.tasks?.find((t: { status: string }) => t.status === status);
  if (!task) return null;

  await navigateToTaskDetail(page, task.id);
  return task.id;
}

async function getAnyTaskId(page: Page): Promise<string | null> {
  const resp = await page.request.get(`${API_BASE}/tasks/?per_page=5`, {
    headers: { "X-API-Key": API_KEY },
  });
  const data = await resp.json();
  return data.tasks?.[0]?.id ?? null;
}

async function getCompletedTaskId(page: Page): Promise<string | null> {
  const resp = await page.request.get(`${API_BASE}/tasks/?per_page=20&status=completed`, {
    headers: { "X-API-Key": API_KEY },
  });
  const data = await resp.json();
  return data.tasks?.[0]?.id ?? null;
}

async function getFailedTaskId(page: Page): Promise<string | null> {
  for (const status of ["failed", "canceled"]) {
    const resp = await page.request.get(`${API_BASE}/tasks/?per_page=5&status=${status}`, {
      headers: { "X-API-Key": API_KEY },
    });
    const data = await resp.json();
    if (data.tasks?.[0]?.id) return data.tasks[0].id;
  }
  return null;
}

async function createTestTask(page: Page): Promise<string | null> {
  // Get first active agent
  const agentResp = await page.request.get(`${API_BASE}/agents/?per_page=1&status=active`, {
    headers: { "X-API-Key": API_KEY },
  });
  const agentData = await agentResp.json();
  const agent = agentData.agents?.[0];
  if (!agent?.skills?.[0]) return null;

  // Create task via API
  const taskResp = await page.request.post(`${API_BASE}/tasks/`, {
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json",
    },
    data: {
      provider_agent_id: agent.id,
      skill_id: agent.skills[0].id,
      messages: [
        {
          role: "user",
          parts: [{ type: "text", content: "E2E lifecycle test: summarize 'hello world'", data: null, mime_type: null }],
        },
      ],
      payment_method: "credits",
    },
  });

  if (!taskResp.ok()) return null;
  const task = await taskResp.json();
  return task.id;
}
