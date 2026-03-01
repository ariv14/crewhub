# CrewHub Marketplace — Comprehensive Test Cases

## A. PUBLIC PAGES (Unauthenticated)

### A1. Homepage (`/`)
| # | Test Case | Type | Result |
|---|-----------|------|--------|
| A1.1 | Page loads without console errors | Smoke | PASS (2026-03-01) |
| A1.2 | Hero section renders with CTA buttons | UI | |
| A1.3 | "Browse Agents" button navigates to `/agents` | Navigation | |
| A1.4 | "Sign In" button navigates to `/login` | Navigation | |
| A1.5 | Feature overview cards render correctly | UI | |
| A1.6 | Page is responsive on mobile viewport (375px) | Responsive | |
| A1.7 | Page is responsive on tablet viewport (768px) | Responsive | |

### A2. Agents Marketplace (`/agents`)
| # | Test Case | Type | Result |
|---|-----------|------|--------|
| A2.1 | Page loads without console errors or 401s | Smoke | PASS (2026-03-01) — 0 errors, 2 benign preload warnings |
| A2.2 | Agent grid renders with cards (up to 12) | UI | |
| A2.3 | Each agent card shows: avatar, name, description, category badge, tags, reputation, latency, tasks count, credits, sparkline | UI | |
| A2.4 | Verified agents show correct badge color (green=audit, purple=quality, blue=namespace) | UI | |
| A2.5 | Search bar accepts input and filters agents by name | Feature | |
| A2.6 | Search query syncs to URL `?q=...` | Feature | |
| A2.7 | Category filter dropdown works and filters results | Feature | |
| A2.8 | Min reputation filter (3.0+, 4.0+, 4.5+) works | Feature | |
| A2.9 | Max credits filter works | Feature | |
| A2.10 | Status filter (Active/Inactive) works | Feature | |
| A2.11 | Pagination controls appear when >12 agents | Feature | |
| A2.12 | Clicking an agent card navigates to `/agents/[id]` | Navigation | |
| A2.13 | No prefetch 404s in console when hovering agent cards | Regression | |
| A2.14 | No chart dimension warnings in console | Regression | |
| A2.15 | Page accessible without login (no redirect to `/login`) | Auth | PASS (2026-03-01) — no redirect |
| A2.16 | Empty state shows when no agents match filters | UX | |
| A2.17 | Mobile layout: cards stack in single column | Responsive | |

### A3. Agent Detail (`/agents/[id]`)
| # | Test Case | Type | Result |
|---|-----------|------|--------|
| A3.1 | Page loads via client-side navigation from `/agents` | Smoke | |
| A3.2 | Agent header shows: avatar, name, description, status badge, verification badge | UI | |
| A3.3 | Stats display: reputation, avg latency, tasks completed, success rate | UI | |
| A3.4 | Skills list renders with input/output modes and examples | UI | |
| A3.5 | Pricing table shows tiers with features | UI | |
| A3.6 | Conversation starters render (if available) | UI | |
| A3.7 | "Try Agent" panel is functional | Feature | |
| A3.8 | Tags and category are displayed | UI | |
| A3.9 | Version info is shown | UI | |
| A3.10 | Page accessible without login | Auth | PASS (2026-03-01) — all 5 agents accessible |
| A3.11 | Direct URL navigation works (e.g. paste URL in browser) | Navigation | PASS (2026-03-01) — all 5 agents load with correct h1 and URL |
| A3.12 | Back navigation returns to `/agents` | Navigation | |

### A4. Category Browse (`/categories/[slug]`)
| # | Test Case | Type | Result |
|---|-----------|------|--------|
| A4.1 | Page loads for valid category slugs (code, data, writing, etc.) | Smoke | PASS (2026-03-01) — general, code, data, writing all HTTP 200 |
| A4.2 | Only agents of that category are shown | Feature | |
| A4.3 | Category title/header matches the slug | UI | PASS (2026-03-01) — h1 matches slug |
| A4.4 | Navigation back to agents marketplace works | Navigation | |

### A5. Login Page (`/login`)
| # | Test Case | Type | Result |
|---|-----------|------|--------|
| A5.1 | Page renders login form | UI | PASS (2026-03-01) — HTTP 200 |
| A5.2 | Google Sign-In button is visible | UI | |
| A5.3 | "Register" link navigates to `/register` | Navigation | |
| A5.4 | Successful login redirects to `/dashboard` | Auth | |
| A5.5 | Login with redirect param returns to original page | Auth | |
| A5.6 | Invalid credentials show error toast | Error | |

### A6. Register Page (`/register`)
| # | Test Case | Type | Result |
|---|-----------|------|--------|
| A6.1 | Page renders registration form | UI | PASS (2026-03-01) — HTTP 200 |
| A6.2 | Form validates required fields (name, email, password) | Validation | |
| A6.3 | Successful registration redirects to `/dashboard` | Auth | |
| A6.4 | "Login" link navigates to `/login` | Navigation | |

---

## B. AUTHENTICATED USER PAGES

### B1. Dashboard Home (`/dashboard`)
| # | Test Case | Type |
|---|-----------|------|
| B1.1 | Redirects to `/login` when unauthenticated | Auth |
| B1.2 | Shows welcome message with user's name | UI |
| B1.3 | Stat cards render: Available Credits, Active Tasks, Total Tasks, My Agents | UI |
| B1.4 | Quick action buttons work: Browse Agents, Register Agent, Create Task | Feature |
| B1.5 | Activity feed connects and shows live events | Feature |
| B1.6 | Activity feed shows correct icons/colors per event type | UI |
| B1.7 | Activity feed auto-reconnects on disconnect | Resilience |
| B1.8 | Redirects to `/onboarding` if user not onboarded | Auth |
| B1.9 | User sidebar renders with all navigation items | UI |
| B1.10 | Sidebar active link highlights correctly | UI |

### B2. My Agents (`/dashboard/agents`)
| # | Test Case | Type |
|---|-----------|------|
| B2.1 | Table lists user's registered agents | Feature |
| B2.2 | Columns display: Name, Category, Status, Tasks, Reputation, Created | UI |
| B2.3 | "Register Agent" button navigates to `/dashboard/agents/new` | Navigation |
| B2.4 | Clicking agent name navigates to agent detail | Navigation |
| B2.5 | Empty state when user has no agents | UX |

### B3. Register Agent (`/dashboard/agents/new`)
| # | Test Case | Type |
|---|-----------|------|
| B3.1 | 4-step wizard renders with progress indicator | UI |
| B3.2 | Step 1 — Basic Info: name, description, endpoint, version, category, tags, MCP URL, avatar, conversation starters | Form |
| B3.3 | Step 1 — Required field validation (name, description, endpoint) | Validation |
| B3.4 | Step 2 — Skills placeholder renders | UI |
| B3.5 | Step 3 — Pricing: credits per task, billing model, license type | Form |
| B3.6 | Step 4 — Review: shows all entered data for confirmation | UI |
| B3.7 | Back/Next navigation between steps works | Navigation |
| B3.8 | Submit creates agent and redirects to agent detail | Feature |
| B3.9 | Submission error shows toast notification | Error |

### B4. My Tasks (`/dashboard/tasks`)
| # | Test Case | Type |
|---|-----------|------|
| B4.1 | Table lists user's tasks | Feature |
| B4.2 | Columns: Task ID, Status, Skill, Credits, Payment, Created | UI |
| B4.3 | Status badges show correct colors per status | UI |
| B4.4 | "New Task" button navigates to `/dashboard/tasks/new` | Navigation |
| B4.5 | Clicking task navigates to task detail | Navigation |
| B4.6 | Empty state when user has no tasks | UX |

### B5. Task Detail (`/dashboard/tasks/[id]`)
| # | Test Case | Type |
|---|-----------|------|
| B5.1 | Task info renders: ID, agent, skill, status, credits | UI |
| B5.2 | Message thread shows user ↔ agent conversation | Feature |
| B5.3 | Artifacts/outputs display correctly | Feature |
| B5.4 | Status timeline shows progression | UI |
| B5.5 | Cancel button works for active tasks | Feature |
| B5.6 | Rating form appears for completed tasks | Feature |
| B5.7 | Star rating (1-5) + comment submission works | Feature |
| B5.8 | Real-time polling updates task status (5s interval) | Feature |
| B5.9 | Send message to agent during task execution | Feature |

### B6. Credits (`/dashboard/credits`)
| # | Test Case | Type |
|---|-----------|------|
| B6.1 | Balance card shows available credits | UI |
| B6.2 | Quick-buy buttons (100, 500, 1000) are clickable | Feature |
| B6.3 | Purchase credits triggers Stripe checkout | Feature |
| B6.4 | Transaction history table renders | UI |
| B6.5 | Transaction types show correct badges (purchase, refund, bonus, debit) | UI |
| B6.6 | No 401 errors in console | Regression |

### B7. Team Management (`/dashboard/team`)
| # | Test Case | Type |
|---|-----------|------|
| B7.1 | Organization switcher dropdown works | Feature |
| B7.2 | Members tab: list members with roles | UI |
| B7.3 | Invite member by email with role assignment | Feature |
| B7.4 | Role options: Viewer, Member, Admin | Feature |
| B7.5 | Teams tab: list teams | UI |
| B7.6 | Create new team | Feature |
| B7.7 | Delete team with confirmation | Feature |

### B8. Settings (`/dashboard/settings`)
| # | Test Case | Type |
|---|-----------|------|
| B8.1 | Profile tab: shows name and email | UI |
| B8.2 | API Keys tab: generate key with custom name | Feature |
| B8.3 | API Keys tab: generated key shown once, copyable | Feature |
| B8.4 | LLM Keys tab: shows configured providers | UI |
| B8.5 | LLM Keys tab: add/update OpenAI key | Feature |
| B8.6 | LLM Keys tab: add/update Gemini key | Feature |
| B8.7 | LLM Keys tab: add/update Anthropic key | Feature |
| B8.8 | LLM Keys tab: add/update Cohere key | Feature |
| B8.9 | LLM Keys tab: delete a key | Feature |
| B8.10 | LLM Keys tab: show/hide password toggle | UI |
| B8.11 | Subscription banner shows Free/Premium status | UI |
| B8.12 | Upgrade to Premium button triggers Stripe | Feature |
| B8.13 | Manage billing portal (for premium users) | Feature |
| B8.14 | Tab switching works (Profile → API Keys → LLM Keys) | Navigation |

### B9. Import from OpenClaw (`/dashboard/import`)
| # | Test Case | Type |
|---|-----------|------|
| B9.1 | Import form renders: Skill URL, Category, Credits, Tags | UI |
| B9.2 | Valid URL submission creates an agent | Feature |
| B9.3 | Success page shows agent link | Feature |
| B9.4 | Invalid URL shows validation error | Validation |

### B10. Onboarding (`/onboarding`)
| # | Test Case | Type |
|---|-----------|------|
| B10.1 | Wizard renders with 6 steps | UI |
| B10.2 | Progress bar advances per step | UI |
| B10.3 | Step 1 — Welcome: name input | Form |
| B10.4 | Step 2 — API Keys: configuration instructions | UI |
| B10.5 | Step 3 — Interests: category selection | Feature |
| B10.6 | Step 4 — Recommended: agents based on interests | Feature |
| B10.7 | Step 5 — Try It: test an agent | Feature |
| B10.8 | Step 6 — Success: completion message | UI |
| B10.9 | Back/Next navigation between steps | Navigation |
| B10.10 | Completion saves preferences and redirects to dashboard | Feature |

---

## C. ADMIN PAGES

### C1. Admin Overview (`/admin`)
| # | Test Case | Type |
|---|-----------|------|
| C1.1 | Redirects non-admin users | Auth |
| C1.2 | KPI cards: Platform Status, Total Users, Total Agents, Total Tasks | UI |
| C1.3 | Transaction volume and task completion rate display | UI |
| C1.4 | Health indicator shows status | UI |
| C1.5 | Auto-refresh every 30s | Feature |
| C1.6 | Admin sidebar renders with all 10 nav items | UI |
| C1.7 | Sidebar collapse/expand toggle works | Feature |
| C1.8 | Collapsed sidebar shows tooltips on hover | UX |

### C2. Admin Users (`/admin/users`)
| # | Test Case | Type |
|---|-----------|------|
| C2.1 | Data table lists all users with sortable columns | Feature |
| C2.2 | Search by email works | Feature |
| C2.3 | Activate/Deactivate user action works | Feature |
| C2.4 | Grant/Revoke Admin action works | Feature |
| C2.5 | Status badges (Active/Inactive) display correctly | UI |

### C3. Admin Agents (`/admin/agents`)
| # | Test Case | Type |
|---|-----------|------|
| C3.1 | Data table lists all agents | Feature |
| C3.2 | Search by name works | Feature |
| C3.3 | Verification level badges show correct colors | UI |
| C3.4 | Status column shows active/inactive/suspended | UI |
| C3.5 | Clicking agent navigates to admin agent detail | Navigation |

### C4. Admin Agent Detail (`/admin/agents/[id]`)
| # | Test Case | Type |
|---|-----------|------|
| C4.1 | Full agent details are displayed | UI |
| C4.2 | Admin actions available (status change, verification) | Feature |

### C5. Admin Tasks (`/admin/tasks`)
| # | Test Case | Type |
|---|-----------|------|
| C5.1 | Data table lists all platform tasks | Feature |
| C5.2 | Auto-refresh every 5s | Feature |
| C5.3 | Search by task ID works | Feature |
| C5.4 | Total task count displayed | UI |
| C5.5 | Sortable columns (Credits, Created) | Feature |

### C6. Admin Transactions (`/admin/transactions`)
| # | Test Case | Type |
|---|-----------|------|
| C6.1 | Data table lists all transactions | Feature |
| C6.2 | Search by description works | Feature |
| C6.3 | Transaction type badges display correctly | UI |
| C6.4 | Sortable columns (Amount, Date) | Feature |

### C7. Admin Governance (`/admin/governance`)
| # | Test Case | Type |
|---|-----------|------|
| C7.1 | Verification queue lists unverified agents | Feature |
| C7.2 | Count of pending verifications shown | UI |
| C7.3 | Table: Agent Name, Category, Verification Level, Date | UI |

### C8. Admin Health (`/admin/health`)
| # | Test Case | Type |
|---|-----------|------|
| C8.1 | API Status card shows Healthy/Unhealthy | UI |
| C8.2 | Registered/Active agent counts display | UI |
| C8.3 | Auto-refresh every 30s | Feature |

### C9. Admin Settings (`/admin/settings`)
| # | Test Case | Type |
|---|-----------|------|
| C9.1 | Configuration values display correctly | UI |
| C9.2 | Values: Fee Rate 10%, New User Bonus 100, Health Check 60s, Rate Limit 100/60s, Receipt Timeout 10min | UI |

### C10. MCP Playground (`/admin/mcp`)
| # | Test Case | Type |
|---|-----------|------|
| C10.1 | Available tools fetched from `/mcp` endpoint | Feature |
| C10.2 | Tool selector dropdown works | UI |
| C10.3 | JSON parameter input accepts valid JSON | Validation |
| C10.4 | Execute button calls tool and displays JSON result | Feature |

### C11. LLM Call Inspector (`/admin/calls`)
| # | Test Case | Type |
|---|-----------|------|
| C11.1 | Data table shows outbound LLM calls | Feature |
| C11.2 | Columns: Timestamp, Provider, Model, Status, Latency, Tokens | UI |
| C11.3 | Filter by agent ID works | Feature |
| C11.4 | Status badges (green 200s, red errors) | UI |

---

## D. GLOBAL / CROSS-CUTTING

### D1. Navigation & Layout
| # | Test Case | Type |
|---|-----------|------|
| D1.1 | Top nav renders on all marketplace pages | UI |
| D1.2 | Mobile hamburger menu opens/closes | Responsive |
| D1.3 | Mobile menu shows correct nav links | Responsive |
| D1.4 | Desktop nav shows inline links | UI |
| D1.5 | Credits badge in nav shows balance (authenticated) | UI |
| D1.6 | Credits badge hidden (unauthenticated) | Auth |
| D1.7 | User dropdown: profile info, dashboard, settings, logout | UI |
| D1.8 | Admin link appears in dropdown for admins only | Auth |
| D1.9 | Logo click navigates to home | Navigation |

### D2. Command Palette
| # | Test Case | Type |
|---|-----------|------|
| D2.1 | Opens with Cmd/Ctrl + K | Feature |
| D2.2 | Shows only public items when unauthenticated | Auth |
| D2.3 | Shows public + dashboard items when authenticated | Auth |
| D2.4 | Shows admin items for admin users | Auth |
| D2.5 | Search filters commands | Feature |
| D2.6 | Selecting item navigates to correct route | Navigation |
| D2.7 | "No results found" for unmatched queries | UX |
| D2.8 | Closes on item selection | UX |
| D2.9 | Closes on Escape key | UX |

### D3. Theme
| # | Test Case | Type |
|---|-----------|------|
| D3.1 | Theme toggle switches between light and dark | Feature |
| D3.2 | Theme persists across page navigation | Feature |
| D3.3 | Theme persists across browser refresh | Feature |
| D3.4 | All pages render correctly in light mode | UI |
| D3.5 | All pages render correctly in dark mode | UI |

### D4. Toast Notifications
| # | Test Case | Type |
|---|-----------|------|
| D4.1 | Success toast shows on successful actions | UX |
| D4.2 | Error toast shows on failed actions | Error |
| D4.3 | Toast auto-dismisses after timeout | UX |
| D4.4 | Toast shows correct icon per type (success/error/info/warning) | UI |

### D5. Loading & Error States
| # | Test Case | Type |
|---|-----------|------|
| D5.1 | Skeleton screens show while data loads | UX |
| D5.2 | Empty states show when no data available | UX |
| D5.3 | Error boundary catches and displays runtime errors | Error |
| D5.4 | Error page shows "Try again" button | Error |

### D6. Auth Guards & Middleware
| # | Test Case | Type |
|---|-----------|------|
| D6.1 | Unauthenticated access to `/dashboard/*` redirects to `/login` | Auth |
| D6.2 | Unauthenticated access to `/admin/*` redirects to `/login` | Auth |
| D6.3 | Non-admin access to `/admin/*` is blocked | Auth |
| D6.4 | Login redirect includes `?redirect=` param | Auth |
| D6.5 | After login, user returns to originally requested page | Auth |
| D6.6 | Logout clears auth state and redirects to home | Auth |
| D6.7 | Expired token doesn't cause console errors on public pages | Regression |

### D7. Console Cleanliness
| # | Test Case | Type | Result |
|---|-----------|------|--------|
| D7.1 | No 401 errors on any public page | Regression | PASS (2026-03-01) — 0 auth errors on public pages |
| D7.2 | No prefetch 404s on agents page | Regression | PASS (2026-03-01) — `__fallback` rename fixed redirect loops |
| D7.3 | No chart dimension warnings | Regression | |
| D7.4 | No unhandled promise rejections | Regression | |
| D7.5 | No React hydration mismatches | Regression | |

---

## E. AGENT EXECUTION LIFECYCLE (End-to-End Workflows)

### E1. Agent Discovery → Task Delegation
| # | Test Case | Type |
|---|-----------|------|
| E1.1 | Browse `/agents` → click agent → view detail → see skills list | E2E |
| E1.2 | Agent detail shows available skills with input/output modes | UI |
| E1.3 | Agent detail shows pricing tiers with billing model (per_task, per_token, per_minute, tiered) | UI |
| E1.4 | Agent detail shows license type (open, freemium, commercial, subscription, trial) | UI |
| E1.5 | Agent detail shows SLA: avg latency, uptime %, success rate | UI |
| E1.6 | Agent detail shows accepted payment methods (credits, x402) | UI |
| E1.7 | Agent detail tabs work: Overview, Skills, Pricing, Try It, A2A Card, Protocols | Navigation |

### E2. Try Agent Panel
| # | Test Case | Type |
|---|-----------|------|
| E2.1 | "Try It" tab renders the TryAgentPanel component | UI |
| E2.2 | Skill selector dropdown lists all agent skills | UI |
| E2.3 | Conversation starters render as clickable badges | UI |
| E2.4 | Clicking conversation starter populates the input | Feature |
| E2.5 | Typing a message and submitting creates a task | Feature |
| E2.6 | Task status indicator shows "working" during execution | UI |
| E2.7 | Agent response streams back into the panel | Feature |
| E2.8 | Panel shows error toast if task creation fails | Error |
| E2.9 | Panel works when user is authenticated | Auth |
| E2.10 | Panel prompts login when user is unauthenticated | Auth |

### E3. Task Creation
| # | Test Case | Type |
|---|-----------|------|
| E3.1 | `POST /tasks/` with provider_agent_id, skill_id, messages creates task | API |
| E3.2 | Task is created with status "submitted" | State |
| E3.3 | Initial message includes `role: "user"` and `parts: [{ type: "text", content }]` | Data |
| E3.4 | Optional max_credits sets spending cap | Feature |
| E3.5 | Optional tier selects pricing tier | Feature |
| E3.6 | Payment method defaults to "credits" | Feature |
| E3.7 | Payment method "x402" triggers pending_payment flow | Feature |
| E3.8 | Task creation fails gracefully if insufficient credits | Error |
| E3.9 | Task creation fails gracefully if agent is inactive/suspended | Error |

### E4. Task Status Lifecycle
| # | Test Case | Type |
|---|-----------|------|
| E4.1 | Status "submitted" → task queued, awaiting agent | State |
| E4.2 | Status "pending_payment" → waiting for x402 receipt (10 min timeout) | State |
| E4.3 | Status "working" → agent actively processing | State |
| E4.4 | Status "input_required" → agent needs more info from client | State |
| E4.5 | Status "completed" → agent finished, artifacts available | State |
| E4.6 | Status "failed" → agent encountered error | State |
| E4.7 | Status "canceled" → client canceled the task | State |
| E4.8 | Status "rejected" → agent declined the task | State |
| E4.9 | Status timeline component renders all transitions with timestamps | UI |
| E4.10 | Status badge colors match status type (green=completed, red=failed, yellow=working, etc.) | UI |
| E4.11 | Real-time polling (5s) detects status changes automatically | Feature |

### E5. Message Exchange During Task
| # | Test Case | Type |
|---|-----------|------|
| E5.1 | Message thread displays user messages (right-aligned, blue) | UI |
| E5.2 | Message thread displays agent messages (left-aligned, muted) | UI |
| E5.3 | Message parts render correctly: text content | UI |
| E5.4 | Message parts render correctly: structured JSON data | UI |
| E5.5 | Message parts render correctly: file attachments with mime_type | UI |
| E5.6 | When status = "input_required", message input field appears | Feature |
| E5.7 | Sending a message via `POST /tasks/{id}/message` updates the thread | Feature |
| E5.8 | New messages appear without full page refresh (polling) | Feature |
| E5.9 | Empty message validation prevents blank submissions | Validation |

### E6. Artifacts & Output
| # | Test Case | Type |
|---|-----------|------|
| E6.1 | Artifacts section appears when task has outputs | UI |
| E6.2 | Text artifacts render inline | UI |
| E6.3 | Image artifacts render with preview (mime_type: image/*) | UI |
| E6.4 | JSON/data artifacts render in formatted viewer | UI |
| E6.5 | Each artifact shows name and metadata | UI |
| E6.6 | Artifacts are accessible after task completion | Feature |

### E7. Task Cancellation
| # | Test Case | Type |
|---|-----------|------|
| E7.1 | Cancel button visible when status in [submitted, pending_payment, working] | UI |
| E7.2 | Cancel button hidden when status in [completed, failed, canceled, rejected] | UI |
| E7.3 | Clicking cancel shows confirmation dialog | UX |
| E7.4 | Confirming cancellation calls `POST /tasks/{id}/cancel` | Feature |
| E7.5 | Task transitions to "canceled" status after cancellation | State |
| E7.6 | Credits are refunded/unreserved after cancellation | Feature |

### E8. Payment — Credits
| # | Test Case | Type |
|---|-----------|------|
| E8.1 | Credits balance shows: total, available, reserved | UI |
| E8.2 | Creating a task with payment_method="credits" reserves credits | Feature |
| E8.3 | credits_quoted shows estimated cost at task creation | Data |
| E8.4 | credits_charged shows actual cost at task completion | Data |
| E8.5 | Task completion deducts credits_charged from balance | Feature |
| E8.6 | Task failure/cancellation releases reserved credits | Feature |
| E8.7 | Transaction history shows task_payment entries | Feature |
| E8.8 | Insufficient balance prevents task creation with clear error message | Error |
| E8.9 | Purchase credits (100, 500, 1000) via Stripe checkout | Feature |
| E8.10 | After purchase, balance updates and transaction recorded | Feature |

### E9. Payment — x402 Protocol
| # | Test Case | Type |
|---|-----------|------|
| E9.1 | Selecting payment_method="x402" at task creation | Feature |
| E9.2 | Task enters "pending_payment" status awaiting receipt | State |
| E9.3 | Receipt submission form: tx_hash, chain, token, amount, payer, payee | Form |
| E9.4 | `POST /tasks/{id}/x402-receipt` submits the receipt | API |
| E9.5 | Backend verifies receipt → response: `{ verified: true, task_status }` | Feature |
| E9.6 | Verified receipt transitions task from pending_payment → working | State |
| E9.7 | Invalid receipt shows verification failure | Error |
| E9.8 | Receipt timeout (10 min) auto-cancels task | Feature |

### E10. Task Rating
| # | Test Case | Type |
|---|-----------|------|
| E10.1 | Rating form appears only when status="completed" AND no existing rating | UI |
| E10.2 | 5-star rating selector with hover preview | UI |
| E10.3 | Optional comment text field | Form |
| E10.4 | Submit rating calls `POST /tasks/{id}/rate` | API |
| E10.5 | After rating, form hides and score displays | Feature |
| E10.6 | Rating form hidden for failed/canceled/rejected tasks | UI |
| E10.7 | Rating form hidden if already rated (client_rating != null) | UI |
| E10.8 | Agent reputation_score reflects accumulated ratings | Feature |

### E11. A2A Protocol & Agent Card
| # | Test Case | Type |
|---|-----------|------|
| E11.1 | "A2A Card" tab renders agent's A2A card JSON | UI |
| E11.2 | A2A card contains: name, description, URL, version, capabilities, skills | Data |
| E11.3 | A2A card shows security_schemes | Data |
| E11.4 | A2A card shows default input/output modes | Data |
| E11.5 | `GET /agents/{id}/a2a-card` returns valid AgentCardResponse | API |

### E12. Protocol Status Display
| # | Test Case | Type |
|---|-----------|------|
| E12.1 | "Protocols" tab shows A2A protocol status (Active if endpoint set) | UI |
| E12.2 | MCP protocol status (Active if mcp_server_url set) | UI |
| E12.3 | ANP protocol status (Verified if DID set, format: did:wba) | UI |
| E12.4 | Inactive protocols show appropriate disabled state | UI |

### E13. Agent Registration → First Task (Full Journey)
| # | Test Case | Type |
|---|-----------|------|
| E13.1 | Register new agent with name, description, endpoint, category | E2E |
| E13.2 | Set skills with input/output modes | E2E |
| E13.3 | Configure pricing (credits per task, billing model, license) | E2E |
| E13.4 | Review and submit → agent created successfully | E2E |
| E13.5 | Agent appears in "My Agents" list | E2E |
| E13.6 | Agent appears in marketplace `/agents` | E2E |
| E13.7 | Another user can discover and view agent detail | E2E |
| E13.8 | Another user creates task via "Try Agent" panel | E2E |
| E13.9 | Task progresses through lifecycle (submitted → working → completed) | E2E |
| E13.10 | Credits are charged and transaction recorded | E2E |
| E13.11 | Client rates the completed task | E2E |
| E13.12 | Agent reputation score updates after rating | E2E |

### E14. Agent Stats & Performance
| # | Test Case | Type |
|---|-----------|------|
| E14.1 | `GET /agents/{id}/stats` returns daily_tasks data | API |
| E14.2 | Sparkline chart renders task activity (last N days) | UI |
| E14.3 | Sparkline shows flat line when no task data | UI |
| E14.4 | Agent card displays total_tasks_completed count | UI |
| E14.5 | Agent detail shows avg_latency_ms (formatted: ms or seconds) | UI |
| E14.6 | Agent detail shows success_rate percentage | UI |

### E15. Usage Quotas & Limits
| # | Test Case | Type |
|---|-----------|------|
| E15.1 | Pricing tier shows daily_tasks quota | UI |
| E15.2 | Pricing tier shows monthly_tasks quota | UI |
| E15.3 | Pricing tier shows max_tokens_per_task limit | UI |
| E15.4 | Pricing tier shows rate_limit_rpm (requests per minute) | UI |
| E15.5 | Exceeding quota shows appropriate error | Error |

---

## Summary

| Section | Count |
|---------|-------|
| A. Public Pages | 40 |
| B. Authenticated User Pages | 55 |
| C. Admin Pages | 30 |
| D. Global / Cross-Cutting | 30 |
| E. Agent Execution Lifecycle | 95 |
| **Total** | **~250 test cases** |

### Priority for Automated Testing (Playwright)
1. **P0 — Smoke**: All pages load without errors (A1.1, A2.1, A2.15, D7.*)
2. **P1 — Auth guards**: Protected routes redirect correctly (D6.*)
3. **P2 — Core discovery**: Agent search, filter, detail view (A2.*, A3.*)
4. **P3 — Task lifecycle**: Create task, status progression, message exchange (E3, E4, E5)
5. **P4 — Payments**: Credits purchase, task payment, balance updates (E8.*)
6. **P5 — Agent registration**: Full agent creation wizard (E13.1–E13.6)
7. **P6 — User workflows**: Rate task, cancel task, try agent panel (E10, E7, E2)
8. **P7 — Admin**: Overview stats, user/agent management (C1–C3)
9. **P8 — UX polish**: Responsive, theme, command palette (D1–D3)
10. **P9 — Protocols**: A2A card, MCP, ANP, x402 payment (E11, E12, E9)

---

## F. TEST EXECUTION LOG

### P0 Smoke Tests — Run 2026-03-01 (staging)

**Environment:** `crewhub-marketplace-staging.pages.dev` (Cloudflare Pages)
**Branch:** `staging` (commit `b78bdf0`)
**Tool:** Playwright MCP (headless Chromium)

| # | Test | Result | Notes |
|---|------|--------|-------|
| A1.1 | Homepage loads | **PASS** | h1: "The Marketplace for AI Agent Collaboration" |
| A2.1 | Agents listing loads | **PASS** | h1: "Agent Marketplace", 0 errors, 2 benign preload warnings |
| A2.15 | Agents accessible without login | **PASS** | No redirect to `/login` |
| A3.10 | Agent detail accessible without login | **PASS** | All 5 agents accessible |
| A3.11 | Agent detail direct URL (all 5 agents) | **PASS** | All return HTTP 200, correct h1, URL stays correct |
| A4.1 | Categories direct URL (general, code, data, writing) | **PASS** | All HTTP 200, h1 matches slug |
| A5.1 | Login page loads | **PASS** | HTTP 200 |
| A6.1 | Register page loads | **PASS** | HTTP 200 |
| D7.1 | No 401 errors on public pages | **PASS** | 0 auth errors |
| D7.2 | No prefetch redirect loops on agents page | **PASS** | `__fallback` rename eliminated ERR_TOO_MANY_REDIRECTS |

**Agents tested (direct URL navigation):**
| Agent | ID | HTTP | h1 Match | URL Correct |
|-------|----|------|----------|-------------|
| Research Agent | `69d017da-c422-402a-80c5-feeaaaa9c0c1` | 200 | Yes | Yes |
| Data Analyst | `1e03ab82-e292-4f76-b3f5-9c0048ccd5de` | 200 | Yes | Yes |
| Python Code Reviewer | `5d35067f-3ac9-4271-880b-f8181bb17391` | 200 | Yes | Yes |
| Universal Translator | `7a4aa975-e0a5-4028-bf8e-12944b0b81ad` | 200 | Yes | Yes |
| Text Summarizer | `93ea8c44-56d8-4860-8c89-8ce0f2ccc004` | 200 | Yes | Yes |

**Known non-blocking issues:**
- A2A card API returns 404 for all agents (no A2A cards configured — API-level, not a page bug)
- Resource preload warnings on some pages (benign browser-level optimization hints)

**Fixes deployed for this run:**
1. `e6bdb49` — Make SPA fallback step resilient to missing shell files
2. `d27a676` — Wake up API before build, remove broken `_worker.js` shell approach
3. `d711971` — Use `per_page=100` in generateStaticParams (API max is 100)
4. `c5e728f` — Enable `trailingSlash` for static export (Cloudflare Pages compatibility)
5. `b78bdf0` — Rename `_` fallback to `__fallback` (avoid Cloudflare redirect loops)
