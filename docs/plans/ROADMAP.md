# CrewHub Development Roadmap

**Last updated:** 2026-03-21
**Staging:** marketplace-staging.aidigitalcrew.com | arimatch1-crewhub-staging.hf.space
**Production:** crewhubai.com | arimatch1/crewhub (HF Space)
**API:** api.crewhubai.com (prod) | api-staging.crewhubai.com (staging)

---

## Completed Work

### Production-Readiness (Mar 5) — MERGED TO MAIN
- [x] UI bug fixes (`/message` → `/messages`, `dynamicParams`, conditional polling)
- [x] Task creation page `/dashboard/tasks/new` with Suspense
- [x] Backend hardening: Sentry SDK, request tracing, Redis rate limiter, input validators, HTTPS enforcement
- [x] Firebase token refresh, push notifier, startup validation, health endpoint
- [x] Playwright E2E: 13 tests (browse, try-it, task-creation, task-lifecycle)
- [x] CI: PostgreSQL-only, lint+test pipeline

### AI Agency Suite (Mar 5) — DEPLOYED ON STAGING
- [x] 56 agent personalities from msitarzewski/agency-agents across 9 HF Spaces
- [x] Parameterized codebase (`demo_agents/agency/`), configured via `DIVISION` env var
- [x] All 9 divisions registered (56 total skills), Try It panel verified E2E
- [x] Deploy script + GitHub Actions workflow

### Auto-Delegation (Mar 5) — ON STAGING
- [x] `POST /api/v1/tasks/suggest` — ranked (agent, skill) suggestions
- [x] Task creation: auto/manual mode toggle with suggestion cards
- [x] Try-agent panel: debounced skill hint after 20+ chars
- [x] 38 backend tests, Playwright updated for mode toggle

### Streamlined Developer Journey (Mar 7) — ON STAGING (9/10 complete)
- [x] Backend: detect endpoint public (no auth, IP rate limited)
- [x] `/register-agent` page with 3-step flow (paste → review → register)
- [x] `RegisterAgentFlow` component with detect mutation, sign-in gate, pricing config
- [x] Frontend API: `detectAgent()` + `useDetectAgent()` hook
- [x] Dashboard welcome state for new users (replaces 6-step onboarding wizard)
- [x] Old onboarding deleted (route, wizard, all step components)
- [x] Landing page: two side-by-side CTAs ("Browse Agents" + "Register Your Agent")
- [x] Agent settings page at `/dashboard/agents/[id]` (edit, re-detect, deactivate, delete)
- [x] Agent detail page: "Manage Agent" button for owners
- [x] **E2E test for register-agent flow** (`frontend/e2e/register-agent.spec.ts`)

### Platform Bug Fixes (Mar 7) — ON STAGING, ALL VERIFIED
- [x] Bug #1: Duplicate agent registration → 409 (backend)
- [x] Bug #2: Auth hydration race — no "Sign In" flash (frontend)
- [x] Bug #3: API key auth sets cookie for middleware (frontend)
- [x] Bug #4: Semantic search wired to `POST /discover/` (frontend)
- [x] Bug #5: Onboarding completion on agent registration (frontend)

See `2026-03-07-bug-fixes-progress.md` for details.

### Marketplace Polish (Mar 9-10) — ON STAGING + PRODUCTION
- [x] Comprehensive `/docs` page — 6 sections (Getting Started, Users, Developers, API, Architecture, FAQ)
- [x] Expandable API reference with 30 endpoints across 6 groups (Auth, Agents, Tasks, Discovery, Credits, Crews)
- [x] Security sanitization — removed all internal URLs, thresholds, infra details from public docs
- [x] Custom API domain — `api.aidigitalcrew.com` via Cloudflare Worker proxy (staging + prod)
- [x] Repo made private, GitHub link removed from footer
- [x] Landing page headline — "Every task deserves a specialist." (positive framing)
- [x] Nav logo resized (20px → 28px) with larger brand text
- [x] Free credits corrected in docs (500 → 100 to match backend)
- [x] Feedback widget → Discord webhook (color-coded embeds: bug/feature/general)
- [x] Docs link added to top nav

### Production Launch (Mar 10) — LIVE
- [x] Frontend deployed to Cloudflare Pages (`crewhub-marketplace`, custom domain `marketplace.aidigitalcrew.com`)
- [x] Deploy workflow updated: `deploy-web.yml` triggers on both `main` and `staging`
- [x] Firebase Auth configured on production (`ai-digital-crew` project)
  - [x] GitHub OAuth provider enabled with production callback URL
  - [x] `marketplace.aidigitalcrew.com` added as authorized domain
  - [x] Service account key set as `FIREBASE_CREDENTIALS_JSON` on HF Space
- [x] All 9 agency divisions (56 skills) registered under owner account
- [x] 10 standalone demo agents carried over from staging
- [x] Promptfoo agent built and deployed (`arimatch1/crewhub-agent-promptfoo`)
  - 4 skills: Evaluate Prompt, Red Team Scan, Vulnerability Scan, Compare Models
  - Powered by xAI Grok-3-mini
- [x] Stripe payments enabled (live mode)
  - [x] Credit packs: 500/$5, 2000/$18, 5000/$40, 10000/$70
  - [x] Webhook endpoint configured for production
  - [x] `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_CREDIT_PACKS`, `FRONTEND_URL` set on HF Space
- [x] Owner account funded with 10,000 credits for testing

### Monitoring & Ops (Mar 10) — LIVE
- [x] Concurrent health checks (ThreadPoolExecutor, 14 spaces in ~2s)
- [x] Response time tracking with slow threshold warning (>5s)
- [x] Discord webhook alerts on failures (color-coded embeds, `#healthcheck` channel)
- [x] Production CrewHub + Promptfoo agent added to monitored spaces (14 total)
- [x] Deduplicated scheduled workflow (runs on `main` only, manual trigger from any branch)
- [x] Richer CI summary with markdown table + response times

### Production Hardening (Mar 11-12) — LIVE
- [x] PostgreSQL on Supabase (staging + production, persistent data)
- [x] `DEBUG=false` on production — Swagger hidden, all security checks enforced
- [x] 21 agents registered, data persistent across restarts
- [x] Stripe LIVE mode enabled on production — real payments active
- [x] Docs page: LangChain, CrewAI, Python SDK sections + deploy buttons
- [x] A2A compliance validator endpoint (`/validate/*`)

### Developer Payouts (Mar 12) — MERGED TO MAIN
- [x] Stripe Connect Express integration (onboard, balance, withdraw, history)
  - `POST /payouts/connect/onboard` — create Express account + onboarding URL
  - `GET /payouts/connect/status` — check Connect account status
  - `GET /payouts/balance` — withdrawable + pending clearance balance
  - `POST /payouts/request` — request payout (min 2500 credits / $25)
  - `GET /payouts/history` — paginated payout history
- [x] Payout safety: only `TASK_PAYMENT` earnings are withdrawable (7-day hold)
  - Signup bonus (`BONUS`) — spendable, NOT withdrawable
  - Admin grants (`BONUS`) — spendable, NOT withdrawable
  - Stripe purchases (`PURCHASE`) — spendable, NOT withdrawable
  - Task earnings (`TASK_PAYMENT`) — withdrawable after 7-day clearance
- [x] Admin credit grant endpoint (`POST /admin/credits/grant`)
- [x] Premium subscription removal — billing simplified to credits-only
- [x] Migration 022: `payout_requests` table + user Connect columns
- [x] Frontend: payouts page, API client, hooks, sidebar link
- [x] Webhook cleanup: removed non-existent `transfer.paid`/`transfer.failed` handlers
- [x] Fix: Firebase auth race condition (duplicate user INSERT → IntegrityError)

### Sidebar Consolidation (Mar 13) — LIVE
- [x] 3 grouped sections: Core (Overview, My Agents, My Tasks), Orchestration (Team Mode, Workflows, Schedules), Account (Credits, Payouts, Settings)
- [x] Crews deprecated in favor of Workflows; deprecation banner on crews page
- [x] Team page "Save as Workflow" replaces "Save as Crew"

### Multi-Agent Workflows (Mar 13) — LIVE
- [x] Workflow engine: sequential chaining with step_group parallelization
- [x] Input modes: chain (previous output), original (user input), custom (template with {{prev_output}})
- [x] Per-step instructions, configurable timeouts, per-step cancel
- [x] Workflow run output display + API endpoint for external access
- [x] Credit settlement for user-initiated workflow tasks
- [x] Scheduling: cron-based workflow execution with croniter

### CRO & Landing Page Overhaul (Mar 14-15) — LIVE
- [x] New headline, CTAs, stats, free credits messaging
- [x] Social proof section on homepage
- [x] Mobile UX: hero spacing, touch targets, carousel, contrast
- [x] PWA support — installable from browser
- [x] Sign In always visible on mobile, Get Started Free in menu

### Marketing Agents (Mar 15) — LIVE
- [x] 6 premium marketing AI agents deployed on HF Spaces with Groq LLM
- [x] Added to HF monitoring (23 total monitored spaces)
- [x] Admin bulk-pricing endpoint + pricing update script

### No-Code Agent Builder (Mar 16-17) — LIVE
- [x] Langflow-based visual builder at `/dashboard/builder`
- [x] Cloudflare Worker proxy for iframe cookie handling
- [x] Custom Langflow components: Knowledge Base, Guard, Publish, CrewHub Agent
- [x] Langflow pool infrastructure: deploy script + GitHub Actions workflow
- [x] Builder Tab in Settings — LLM provider guides + HF key setup
- [x] Build Agent link in nav + mobile hamburger menu

### Branding & Domain (Mar 15-16) — LIVE
- [x] Custom domain: `crewhubai.com` (frontend), `api.crewhubai.com` (backend)
- [x] OG image, favicons, SEO metadata, brand guidelines
- [x] Legal pages: Terms of Service, Developer Agreement, Privacy Policy
- [x] Refined logo with orbiting particles, deep indigo color palette

### Agent Orchestration Patterns v0.6.0 (Mar 18) — LIVE
- [x] **Supervisor Agent Pattern** — AI plans workflows from natural language goals (Groq LLM + BYOK)
  - `POST /workflows/supervisor/plan` — generate plan
  - `POST /workflows/supervisor/replan` — regenerate with feedback
  - `POST /workflows/supervisor/approve` — convert to workflow
  - Human-in-the-loop: user reviews, edits, approves before execution
  - Ephemeral plan storage with 1h TTL
  - Rate limiting: 5/hr free, 20/hr BYOK
- [x] **Hierarchical Agent Teams** — workflow steps can contain sub-workflows
  - Cycle detection (BFS graph walk)
  - Depth enforcement (2 levels free, 10 BYOK)
  - Pump ordering: children processed before parents (depth DESC)
  - Cancellation cascade: parent cancel propagates to child runs
  - Timeout inheritance: child respects parent step timeout
- [x] **Interactive Guide Page** (`/guide`) — 12 sections + pattern recommender widget
- [x] **Landing Page Orchestration Showcase** — 3 pattern cards in "Assemble Your AI Team"
- [x] **Pattern Picker** on `/workflows/new` — Manual, Hierarchical, Supervisor
- [x] **Sub-Workflow Editor** — Agent/Sub-Workflow toggle in step cards
- [x] **Supervisor Plan Review UI** — confidence bars, cost estimates, approve/edit/regenerate
- [x] `?pattern_type=` filter on workflow list endpoints
- [x] Migration 028: orchestration patterns schema changes
- [x] 33 new tests (27 unit + 6 E2E)
- [x] Docs page updated with Orchestration API group (4 endpoints)

### Infrastructure Fixes (Mar 18) — LIVE
- [x] GitHub Actions bumped: checkout/setup-node v5, setup-python v6 (Node.js 24 compat)
- [x] Mobile hamburger menu scrollable on short viewports
- [x] Duplicate Build Agent entry removed from mobile menu
- [x] Swagger UI link hidden on production guide page

### Team Mode Merge into Workflows (Mar 18) — LIVE
- [x] Removed Team Mode from desktop nav, mobile menu, and sidebar
- [x] All "Try Team Mode" CTAs replaced with "Create Workflow" / "Try Workflows"
- [x] Guide page: renamed to "Parallel Execution (Team Mode)", updated steps and comparison table
- [x] Explore page: added Supervisor, Hierarchical, No-Code Builder, Guide cards; updated flows
- [x] `/team` page replaced with redirect to `/dashboard/workflows/new` (959 lines removed)
- [x] Sidebar simplified: Workflows, Schedules, Build Agent (3 items, was 4)
- [x] Full production E2E verified — all 14 functional tests pass

### Compact Landing Page + Security Hardening (Mar 19) — LIVE
- [x] Compact "Find the Right Agent" card — textarea → input, 5 starters → 3, floating dropdown
- [x] Security: **64 of 64 compliance findings resolved (100%)**
- [x] AuditLog model + migration 030 + utility wired into all admin endpoints
- [x] SSRF protection, rate limiting, Sentry PII scrubbing, CSP headers, cookie hardening
- [x] GDPR: data export + account deletion endpoints, consent tracking migrations
- [x] RBAC: admin_role column with ops/super/billing separation
- [x] Encryption key versioning with backward-compatible decrypt
- [x] Cookie compliance Phase 1: sidebar_state flags, consent banner text, privacy policy inventory
- [x] Activity stream fix: `Transaction.user_id` → account-based query (was crashing SSE)

### Cookie & Privacy Compliance (Mar 19) — ALL PHASES COMPLETE (LIVE)
- [x] **Phase 1**: sidebar_state flags, privacy policy inventory, session recording disclosure
- [x] **Phase 2**: Cookie Preferences card in Settings, footer link, consent reset flow
- [x] **UX rewrite**: Removed PostHog/session replay jargon from banner + settings card
  - Banner: "We use cookies to understand how you use CrewHub so we can make it better"
  - Settings: plain-language analytics vs essential cookies explanation
  - Vendor details moved to Privacy Policy where they belong (GDPR best practice)
- [ ] **Phase 3**: Server-side consent logging (`POST /auth/consent`, versioned consent key)

### Health Monitor Fix (Mar 20) — ALL PHASES COMPLETE (LIVE)
Post-incident fix after 27 agents mass-deactivated. 18 gaps identified, 18 resolved.
See `docs/plans/2026-03-20-health-monitor-fix.md` for full gap analysis.

- [x] **Phase 0 — Hotfix**: `UNAVAILABLE` status enum, threshold 3→12 (1hr), auto-recovery
  on healthy check, migration 033 (reactivated 27 agents), per-agent error isolation
- [x] **Phase 1 — Frontend UX**: "Unavailable" badge on agent cards, "Offline" label replaces
  Try button, detail page amber warning banner, Try It tab disabled for unavailable agents,
  agent listing returns unavailable agents (visible with badge, not hidden)
- [x] **Phase 2 — Scale + Compliance**: concurrent checks (`asyncio.gather` + Semaphore(10)),
  shared `httpx.AsyncClient` with connection pooling, 401/403/429 treated as "alive",
  audit log on every automated status change, `User-Agent: CrewHub-HealthMonitor/1.0`,
  admin `POST /admin/agents/bulk-reactivate`, admin `GET /admin/health/overview`
- [x] **Phase 3 — Cold-Start + Adaptive**: HF Spaces sleep detection (503 pattern),
  60s wake probe timeout for sleeping agents, adaptive intervals (10min healthy / 2min failing),
  random jitter (0-30s) prevents thundering herd, migration 034 (dedicated health columns:
  `health_failures`, `health_reason`, `last_health_check_at`, `last_healthy_at`,
  `last_health_latency_ms`), JSONB `_health_failures` cleanup

### Admin Platform Control Suite (Mar 20-21) — LIVE
- [x] **Admin Overview Dashboard** (`/admin`) — platform KPIs (users, agents, tasks, transactions), task completion rate, credit grant form, auto-refresh 30s
- [x] **Agent Management** (`/admin/agents`) — sortable listing, dropdown actions per agent (toggle status, set verification, ban/suspend, permanent delete)
- [x] **Governance Verification** (`/admin/governance`) — pending agent queue, bulk verify/certify/demote controls
- [x] **Submissions Review** (`/admin/submissions`) — approve/reject/revoke Langflow-built agents, flow ID tracking
- [x] **Agent Detail** (`/admin/agents/[id]`) — skills tab, pricing tab, raw JSON viewer, error handling
- [x] **Additional Admin Tabs**: Users, Tasks, Transactions, Health, LLM Calls, Settings
- [x] Admin can delete any agent — new admin delete endpoint bypasses ownership check
- [x] MissingGreenlet fix on admin verification update — commit+refresh before serialize

### Landing Page Redesign v2 (Mar 20-21) — LIVE
- [x] **Search-First Hero** — MagicBox elevated to primary position, CTAs demoted to secondary text links
- [x] **Side-by-Side Panels** — Find an Agent + Build a Workflow, equal 1:1 width split on desktop
- [x] **Smart Search UX** — auto-search on chip click, 3-char hint threshold, query passthrough to browse
- [x] **45% Page Reduction** — cut redundant sections, CTA consolidation (15 → 3)
- [x] P1/P2 Polish: pricing clarity, A2A tone, trending skeleton, elevated Magic Box
- [x] Design spec: `docs/superpowers/specs/2026-03-21-landing-page-redesign.md`

### E2E Test Refresh (Mar 21) — LIVE
- [x] Updated tests for current UI — 50/60 pass, 3 flaky, 6 skipped
- [x] Deprecated `team-mode.spec.ts` removed (replaced by workflows)
- [x] Updated: agent-try-it, magic-box, register-agent, task-lifecycle-ux

### Bug Fixes & Polish (Mar 20-21)
- [x] Build My Agent redirects to Langflow builder page
- [x] Workflow detail page freeze — private workflows returned 404 for owner
- [x] Auth credentials passed properly for private workflow access
- [x] CF Worker CORS — replace wildcard `*` with specific origin
- [x] Error state handling for admin agent detail and agent settings pages
- [x] Trailing slashes on dashboard routes + `<a>` tags in welcome cards
- [x] Wrangler version pinned to 3.114.0 for CF Pages deploy stability
- [x] Auth redirect preserves query params — workflow pattern selection survives login flow
  - Middleware: `pathname + request.nextUrl.search` instead of `pathname` alone
  - AuthGuard: `useSearchParams()` wrapped in `<Suspense>` for static export compatibility
  - All 3 patterns verified in browser: manual, hierarchical, supervisor

### Stripe Dashboard Manual Steps (Pending)
- [ ] **Staging**: Enable Stripe Connect (test mode), add `account.updated` webhook event
- [ ] **Staging**: Remove 4 stale subscription webhook events
- [ ] **Production**: Remove 4 stale subscription webhook events (customer.subscription.*, invoice.payment_failed)
- [ ] **Production**: Enable Stripe Connect when ready for real developer payouts

---

## Current Sprint

### Compliance Readiness — FULLY COMPLETE (Mar 21)

**All technical AND documentation compliance work is complete.**

| Item | Type | Status |
|------|------|--------|
| 64/64 security findings | Code | ✅ Resolved |
| Server-side consent logging (`POST /auth/consent`) | Code | ✅ Built (Mar 21) |
| CORS `allow_methods` restricted | Code | ✅ Fixed (Mar 21) — explicit methods + headers |
| `compliance.txt` language | Copy | ✅ Fixed (Mar 21) — "aligned with" not "certified" |
| Incident response procedure | Document | ✅ Created (Mar 21) — `docs/compliance/incident-response-procedure.md` |
| Data Processing Agreement (DPA) | Document | ✅ Created (Mar 21) — `docs/compliance/data-processing-agreement.md` |
| SOC 2 controls mapping (CC1-CC9) | Document | ✅ Created (Mar 21) — `docs/compliance/soc2-controls-mapping.md` |

**Staging verified (Mar 21):** 13/14 backend API tests PASS, 6/6 frontend browser tests PASS.
- Consent endpoint: accept/decline/no-auth/invalid-body all correct
- CORS: explicit methods returned, disallowed origins blocked
- GDPR export: consent fields populated from new endpoint
- Frontend: banner, settings cookie preferences, danger zone all render
- No console errors related to consent changes

**Penetration test completed (Mar 21):** 51 tests across OWASP Top 10.
- Staging: 45/51 PASS, 6 findings (0 critical, 0 high, 3 medium, 3 low)
- All 6 findings remediated and retested: admin self-grant block, name sanitization, HSTS/CSP headers, openapi.json hidden
- Production retest: 6/6 previously failed/skipped items now PASS
- Full report: `docs/compliance/penetration-test-report-2026-03-21.md`
- Second admin account (`aidigitalcrew@gmail.com`) promoted for SOC 2 separation of duties

**Next step: Engage SOC 2 auditor for readiness assessment.**
- [x] ~~Commission penetration test~~ — completed Mar 21 (0 open findings)
- [ ] Select and contact SOC 2 auditor
- [ ] Schedule scoping call

### RBAC Enforcement (Mar 21) — LIVE
- [x] **3-tier role hierarchy** enforced on all 18 admin endpoints:
  - `super_admin` (2): user management, role changes
  - `ops_admin` (12): submissions, agent management, health, re-embed
  - `billing_admin` (3): credits/grant, transactions, tasks list
  - `any admin` (1): platform stats (read-only)
- [x] Fixed NULL `admin_role` bypass — legacy admins no longer skip role checks
- [x] `PUT /admin/users/{id}/role` — promote, demote, or change admin roles
- [x] Self-role-change blocked (prevents lockout)
- [x] `admin_role` exposed in UserResponse schema
- [x] **Admin UI**: color-coded role badges (Super Admin red, Ops blue, Billing amber)
- [x] **Admin UI**: credit grant form detects self-grant, disables button, shows amber warning
- [x] Two-admin setup: `arimatch1` (super_admin) + `aidigitalcrew` (ops_admin)
- [x] All changes verified on staging (9/9 RBAC tests + 2/2 UI tests PASS)

### Multi-Channel Gateway Phase 1-2 (Mar 21-22) — ON STAGING
**Full implementation of gateway service + channel management UI.**

**Backend — Gateway Service (deployed to HF Space `arimatch1/crewhub-gateway`):**
- [x] Gateway FastAPI app with Telegram webhook receiver (<3s ack, async processing)
- [x] Async task callback handler (agent response → platform message)
- [x] `POST /gateway/charge` — atomic credit deduction with daily limit checks
- [x] `GET /gateway/connections/{id}` — decrypted config + blocked users list
- [x] `POST /gateway/heartbeat`, `POST /gateway/log-message`, `POST /gateway/create-task`
- [x] Telegram adapter: parse inbound, send message (4096 char chunking + markdown retry), typing indicator
- [x] In-memory rate limiter (10 msg/min per user) with 60s periodic cleanup
- [x] Message deduplication (5 min TTL + DB unique constraint)
- [x] CrewHub API client with 60s connection cache (non-sensitive fields only)
- [x] Deploy script + GitHub Actions workflow (`deploy-gateway.yml`)
- [x] Gateway secrets configured on staging (GATEWAY_SERVICE_KEY, CREWHUB_API_URL, GATEWAY_PUBLIC_URL)

**Backend — Compliance Hardening (24 findings resolved):**
- [x] C1: Telegram webhook signature verification (per-connection HMAC secret_token)
- [x] C2: Callback URL validation (UUID connection_id, numeric chat_id)
- [x] C3: Bot tokens never cached in memory — `get_bot_token()` fetches on-demand
- [x] H1: Message text capped at 2000 chars, 90-day auto-purge background job
- [x] H2: platform_user_id pseudonymized via HMAC-SHA256 (keyed, per-connection)
- [x] H3: Typed heartbeat schema (Literal status enum, max_length validation)
- [x] H4: `hmac.compare_digest()` for gateway key comparison (timing-safe)
- [x] H5: `POST /gateway/create-task` — proper gateway auth, no fabricated API keys
- [x] H6: Audit logging on all channel mutations (create/update/delete/rotate)
- [x] M1: Security headers middleware on gateway (HSTS, X-Frame, nosniff)
- [x] M2-M7, L1-L2: Rate limiter cleanup, generic errors, data minimization, schema fixes

**Backend — Channel & Customer Management API:**
- [x] Token rotation endpoint (`POST /channels/{id}/rotate-token`)
- [x] Contact aggregation (`GET /channels/{id}/contacts`)
- [x] Per-contact message thread (`GET /channels/{id}/contacts/{hash}/messages`)
- [x] Block/unblock contacts (`POST/DELETE /channels/{id}/contacts/{hash}/block`)
- [x] GDPR erasure (`DELETE /channels/{id}/contacts/{hash}/messages`)
- [x] Paginated message log (`GET /channels/{id}/messages?direction=&cursor=`)
- [x] Admin channel list (`GET /admin/channels/`) with developer info
- [x] Admin channel detail (`GET /admin/channels/{id}`) with owner credit balance
- [x] Admin message access with justification gate (`GET /admin/channels/{id}/messages?justification=`)
- [x] `GatewayConnectionResponse` includes `blocked_users` list for gateway enforcement
- [x] N+1 query fix — batch stats query replaces per-channel loop

**Backend — Privacy & Encryption:**
- [x] Inbound message text NOT stored (NULL) — GDPR Art. 25 privacy by design
- [x] Outbound message text encrypted (Fernet, versioned key `v1:`, dual-key rotation)
- [x] `CHANNEL_MESSAGE_KEY` separate from gateway service key
- [x] Backend-side decryption (`src/core/message_crypto.py`) for developer/admin viewing
- [x] Column renamed: `platform_user_id` → `platform_user_id_hash`

**Database — Migration 036:**
- [x] `channel_contact_blocks` table (connection_id, user_hash, blocked_by, reason)
- [x] `privacy_notice_url` column on `channel_connections`
- [x] `message_retention_days` column (default 90)
- [x] `message_text` nullable (for NULL inbound text)
- [x] Performance index: `(connection_id, platform_user_id_hash, created_at DESC)`

**Frontend — Developer Channel Pages:**
- [x] `/dashboard/channels` — dedicated list page (moved out of Settings tab)
  - Channel cards with platform icon, status badge, agent, today's stats
  - "Connect a Channel" button opens wizard
  - Stats strip: total channels, messages today, credits today
- [x] `/dashboard/channels/[id]` — 5-tab detail page:
  - **Overview**: stats grid (messages, contacts, credits, response time) + recent messages
  - **Contacts**: data table with block/unblock, GDPR delete, message count, last seen
  - **Messages**: timeline with direction filter (All/Inbound/Outbound), privacy placeholder for inbound
  - **Analytics**: Recharts area/bar charts (daily messages + credits, 7/30 day)
  - **Settings**: budget controls, token rotation, pause/resume, danger zone (delete)
- [x] Sidebar updated: Channels → `/dashboard/channels`
- [x] Channels tab removed from Settings page

**Frontend — Admin Channel Pages:**
- [x] `/admin/channels` — DataTable with platform, bot name, developer, agent, status, messages/credits
- [x] `/admin/channels/[id]` — detail with developer info card (name, email, balance, tier)
  - Justification gate on Messages tab (SOC 2 CC7.2): 4 options, audit-logged
  - Audit banner: "Access logged: [justification] — [admin email]"
  - Admin actions: Force Pause, Force Disconnect
- [x] Admin sidebar updated with Channels entry

**Frontend — Shared Components:**
- [x] `channel-card.tsx` — reusable card with platform icons, status badges
- [x] `contact-table.tsx` — contacts with block/unblock/GDPR delete actions
- [x] `message-log.tsx` — timeline with direction filter, privacy placeholder
- [x] `analytics-charts.tsx` — Recharts message volume + credit burn charts
- [x] `admin-access-gate.tsx` — AlertDialog justification selector
- [x] `channel-edit-sheet.tsx` — Sheet for editing budget/config

**Frontend — Compliance in Wizard:**
- [x] Privacy Notice URL (required field, validated as URL)
- [x] HIPAA disclaimer: "No PHI without BAA" warning banner
- [x] Data residency note: "Channel data processed in United States"
- [x] Budget controls editable (not hardcoded): daily limit, low balance, auto-pause

**Testing — 44 tests passing:**
- [x] `tests/test_channels.py` — gateway schema validation, auth, route registration (11 tests)
- [x] `tests/test_gateway.py` — Telegram adapter, rate limiter, dedup, registry (17 tests)
- [x] `tests/test_channel_management.py` — contact/message schemas, crypto roundtrip, HMAC pseudonymization, admin justification, routes (16 tests)

**E2E Verified on Staging (13/13 PASS):**
- Developer: channel list, detail 5 tabs, wizard 4 steps, mobile responsive
- Admin: channel list with developer info, detail with justification gate + audit banner
- Console: no channel-specific JS errors

### Cloudflare Worker Gateway (Mar 22) — LIVE ON STAGING + PRODUCTION ✅
**CF Worker gateway permanently solves HF Spaces DNS restrictions. $0 cost, <1ms latency.**

**E2E verified on staging:** Telegram → CF Worker → backend → agent → CF Worker → Telegram response in ~10 seconds.
**Production deployed:** `crewhub-gateway-production.arimatch1.workers.dev` — secrets set, auth verified.

**Architecture (reusable for Slack, Discord, WhatsApp):**
```
Platform (Telegram/Slack/Discord)
    ↓ webhook
CF Worker Gateway
    Staging:    crewhub-gateway-staging.arimatch1.workers.dev
    Production: crewhub-gateway-production.arimatch1.workers.dev
    ├── Verifies webhook signature (HMAC per-connection)
    ├── Parses message, dedup, rate limit
    ├── Sends typing indicator to platform
    ├── Charges credits via backend API
    ├── Logs inbound message (NULL text — GDPR)
    ├── Creates task via backend API
    ├── Polls GET /gateway/task-status/{id} every 4s (up to 25s)
    ├── Sends agent response to platform
    └── Logs outbound message
    ↓ HTTP calls
HF Space Backend (arimatch1-crewhub-staging.hf.space)
    ├── GET /gateway/connections/{id} — decrypted config + blocked users
    ├── POST /gateway/charge — atomic credit deduction
    ├── POST /gateway/log-message — message logging (dedup via unique constraint)
    ├── POST /gateway/create-task — task creation under channel owner
    └── GET /gateway/task-status/{id} — poll task completion (gateway auth)
    ↓ A2A dispatch
Agent HF Spaces (e.g., arimatch1-crewhub-agency-design)
    └── Processes task, returns artifacts
```

**Implementation details:**
- [x] `cloudflare/gateway-worker.js` — ~300 lines JS, deployed via wrangler
- [x] `cloudflare/wrangler-gateway.toml` — config with cron trigger (`* * * * *`)
- [x] Webhook signature: HMAC-SHA256 per-connection (sha256(service_key:connection_id)[:32])
- [x] Rate limiting: in-memory Map (10 msg/min per user, best-effort)
- [x] Dedup: in-memory Map with 5-min TTL (backup — DB unique constraint is authoritative)
- [x] Task polling: `ctx.waitUntil()` keeps Worker alive after 200 response
- [x] Cron fallback: `scheduled()` handler for tasks that exceed 25s poll window
- [x] Backend: `GET /gateway/task-status/{id}` — gateway-authenticated task status endpoint
- [x] Telegram: `sendMessage` + `sendChatAction` (typing) + 4096-char chunking + Markdown retry
- [x] Secrets: `GATEWAY_SERVICE_KEY`, `BACKEND_URL` set via `wrangler secret`
- [x] Telegram webhook registered to CF Worker URL

**Compliance audit completed (Mar 22):** 12 findings identified, all resolved.
- Full report: `docs/compliance/cf-worker-gateway-audit-2026-03-22.md`

**Fully automated channel creation flow (Mar 22):**
```
Developer in browser:
  1. Wizard: select platform → enter credentials → select agent → Create Channel
  2. Backend: saves channel to Supabase (token format-validated, no external API call)
  3. Browser: POST /auto-register → CF Worker → Telegram setWebhook (auto, permanent)
  4. Done — bot is live, webhook registered, zero manual steps
```
- [x] `/auto-register` endpoint on CF Worker (validates bot token via Telegram getMe)
- [x] Frontend wizard calls `/auto-register` after channel creation (fire-and-forget)
- [x] CSP `connect-src` includes `*.workers.dev` for browser→CF Worker calls
- [x] CORS headers on CF Worker for cross-origin browser requests
- [x] Webhook is permanent — survives all restarts (HF Space, CF Worker, server outages)

**Production E2E verified (Mar 22):**
- Created channel via UI → webhook auto-registered → bot responded on Telegram
- Tested with 3 agents: Design ("bakery color palette"), Translator ("Buenos dias"), Support (10-point support list)
- Response time: ~10-15 seconds
- Credits deducted automatically

**Production deployment record:** `docs/compliance/production-deployment-2026-03-22.md`

**Known limitation:** HF Spaces has intermittent DNS — agent dispatch (backend → agent HF Space)
sometimes fails. After a Space restart, DNS works reliably for hours. Long-term fix: move backend
to Railway ($5/mo) or contact HF support for Pro DNS fix.

**How to add a new platform (Slack, Discord, WhatsApp):**
1. Add platform adapter in `gateway-worker.js`:
   - `handleSlackWebhook(request, env, connectionId)` — parse Slack Events API format
   - `sendSlack(token, channelId, text)` — call Slack `chat.postMessage`
   - Verify Slack request signature (`x-slack-signature` header)
2. Add webhook route in the Worker's `fetch` handler:
   ```javascript
   const slackMatch = url.pathname.match(/^\/webhook\/slack\/([0-9a-f-]+)$/);
   if (slackMatch && request.method === "POST") {
     return handleSlackWebhook(request, env, ctx, slackMatch[1]);
   }
   ```
3. Backend: no changes needed — the gateway API endpoints are platform-agnostic
   (connection lookup, charge, log-message, create-task, task-status all work for any platform)
4. Frontend: add platform to channel wizard (setup instructions, credential fields)
5. Register webhook URL with the platform pointing to the CF Worker

**Cost at scale:**
| Messages/day | CF Worker requests/day | Monthly cost |
|-------------|----------------------|--------------|
| 100 | ~500 | $0 (free tier) |
| 1,000 | ~5,000 | $0 (free tier) |
| 10,000 | ~50,000 | $0 (free tier) |
| 33,000+ | ~100,000+ | $5/mo (paid tier) |

### Near-Term
- [ ] Delegation accuracy analytics query (data captured, no reporting endpoint)
- [ ] Redis-backed embedding rate limiter (current: in-memory, single-process only)
- [ ] Clean up `src/api/telegram_webhook.py` (superseded by CF Worker gateway)
- [ ] Move backend to Railway ($5/mo) for reliable DNS (eliminates agent dispatch failures)
- [ ] Slack + Discord adapters (Multi-Channel Gateway Phase 3)
- [ ] Teams + WhatsApp adapters (Multi-Channel Gateway Phase 4)
- [ ] Channel analytics with real data (Multi-Channel Gateway Phase 5)

### Backlog
- [ ] x402/OpenClaw payment integration (design: `2026-02-27-x402-openclaw-design.md`)
- [ ] Task lifecycle UX enhancement (design: `2026-03-05-task-lifecycle-ux-design.md`)
- [ ] Inline skill editor
- [ ] Promptfoo evaluation integration (demo_agents/promptfoo/)
- [ ] Agent marketplace growth — developer onboarding funnel optimization
- [ ] Performance monitoring / analytics dashboard

### Hybrid Agents — Local/On-Device Execution (Future)

Enable agents running on user hardware to participate in the CrewHub marketplace.
Unlocks privacy-first, regulated industry, and on-device AI use cases.

**Phase 1: Hybrid Agent Registry** (1-2 weeks)
- [ ] `crewhub-tunnel` CLI — secure tunnel (Cloudflare Tunnel) to expose local agents
- [ ] Agent status: `local` badge + online/offline indicator in marketplace
- [ ] A2A gateway routes tasks to local endpoints (no protocol changes needed)
- [ ] Local agents can set price to 0 (self-hosted) or charge credits
- [ ] Heartbeat monitoring — auto-mark offline after 60s no-ping

**Phase 2: Agent Recipes** (2-3 weeks)
- [ ] `crewhub-agent.yaml` spec — portable agent config (model, prompt, tools, skills)
- [ ] Developers publish recipes to marketplace alongside cloud-hosted version
- [ ] `npx crewhub run <agent-id> --gpu auto` — pull recipe, download model from HF Hub, run locally
- [ ] "Run Locally" / "Try in Cloud" toggle on agent detail page
- [ ] Billing: developers earn credits whether agent runs in cloud or on user hardware

**Phase 3: Split Execution in Workflows** (3-4 weeks)
- [ ] Per-step `execution: "local" | "cloud"` setting in workflow editor
- [ ] Lock icon on local steps, cloud icon on cloud steps
- [ ] Orchestration engine routes steps to local tunnel or cloud agent as configured
- [ ] Use case: sensitive data processed locally, non-sensitive steps in cloud

**Phase 4: Agent Swarm Network** (future)
- [ ] Users opt-in to share idle GPU via `crewhub-node` daemon
- [ ] P2P agent compute network with latency-based routing
- [ ] Hosts earn credits for providing compute (3 credits/task)
- [ ] Sandboxed execution (Docker/WASM) — hosts can't inspect data
- [ ] Cheaper than cloud: ~5 credits/task vs 15 credits/task

**Phase 5: Confidential Agent Enclaves** (future, enterprise)
- [ ] TEE support (Intel SGX / AMD SEV / NVIDIA Confidential Computing)
- [ ] Remote attestation — marketplace verifies exact agent code in enclave
- [ ] License-key billing (annual subscription) for enterprise enclaves
- [ ] Provably private execution — nobody (developer, CrewHub, IT) can see data

### Protocol Adoption Roadmap (Future)

CrewHub currently implements A2A and a custom payments system. Adopting additional
standard protocols increases interoperability with the broader AI agent ecosystem.

**Current protocol status:**
- ✅ A2A — fully implemented (JSON-RPC 2.0, agent-card.json discovery, task delegation)
- ⚠️ AP2 — custom equivalent (credit system with reserves, guardrails, spending limits)
- ❌ MCP, UCP, A2UI, AG-UI — not yet adopted

**Phase 1: AG-UI — Real-Time Agent Streaming** (high impact, 1-2 weeks)
- [ ] SSE/WebSocket streaming endpoint for task execution progress
- [ ] "Try It" panel shows live streaming text instead of loading spinner
- [ ] Partial result rendering — agents can emit chunks during processing
- [ ] Progress events: `thinking`, `tool_call`, `partial_result`, `complete`
- [ ] Streaming support in workflow execution (per-step progress)
- [ ] Frontend: streaming message component with typing indicator

**Phase 2: A2UI — Rich Agent UI Components** (2-3 weeks)
- [ ] Agent response schema: structured `ui_components` array alongside text artifacts
- [ ] Component types: `table`, `chart`, `diff`, `form`, `calendar`, `code_block`, `image`
- [ ] Frontend renderer: maps A2UI component types to shadcn/ui components
- [ ] Agent SDK helper: `emit_ui(type="table", data={...})` in agent response
- [ ] Use cases: code review → diff viewer, data agent → charts, marketing → campaign calendar
- [ ] Graceful fallback: agents without A2UI still return plain markdown

**Phase 3: MCP — Tool & Data Access for Agents** (2-3 weeks)
- [ ] MCP client in agent runtime — agents can discover and call external tools
- [ ] Key for Hybrid Agents: local agents use MCP to access user's files, databases, APIs
- [ ] MCP server registry in marketplace — users connect data sources, agents consume
- [ ] Pre-built MCP servers: GitHub, Google Drive, Slack, databases
- [ ] Permission model: user authorizes which MCP servers each agent can access

**Phase 4: AP2 Standard Compliance** (1-2 weeks)
- [ ] Align credit system with AP2 spec (cryptographic proof of payment intent)
- [ ] AP2 payment receipts for agent-to-agent transactions
- [ ] Configurable guardrails via AP2 standard format (spending limits, merchant allowlists)
- [ ] Enables CrewHub agents to transact with agents outside the platform

**Phase 5: UCP — Agent Commerce** (future)
- [ ] Agents can purchase goods/services on behalf of users
- [ ] UCP-standard order schema (what, from whom, delivery)
- [ ] Integration with AP2 for payment authorization
- [ ] Use cases: procurement agent, booking agent, supply chain agent
- [ ] Merchant verification and dispute resolution

### Resilience & Multi-Cloud Readiness (Future)

Current backend is a single HF Space (1 container, 1 worker, 1 region). The CF Worker
proxy at `api.crewhubai.com` already acts as the **API Gateway** — the key abstraction
layer that makes backend failover and multi-cloud possible without any client changes.

```
Clients → CF Worker (gateway) → Primary (HF Space) / Secondary (Railway/Fly)
                                         ↓
                                  Supabase PostgreSQL
```

**Tier 1: Harden within HF** (1 day)
- [ ] Bump to 4 uvicorn workers in `Dockerfile.hf` (4x throughput, crash isolation)
- [ ] SQLAlchemy connection pooling (`pool_size=10, max_overflow=20`)
- [ ] Move Alembic migrations from FastAPI lifespan to CI step (multi-instance safe)
- [ ] Move in-memory rate limiter to Upstash Redis (shared across workers/instances)
- [ ] CF Worker returns cached fallback during backend downtime (static status page)

**Tier 2: Active-passive failover** (1-2 weeks)
- [ ] Deploy standby backend on Railway (same Dockerfile, same env vars, $5/mo)
- [ ] CF Worker health-check routing: try primary (5s timeout) → fallback to secondary
- [ ] GitHub Actions parallel deploy: HF Space + Railway on push to main/staging
- [ ] Move embedding cache from in-memory to Redis (shared across instances)
- [ ] Zero-downtime deploys: deploy to standby, health-check, swap routing weight

**Tier 3: Active-active multi-cloud** (future)
- [ ] CF Worker weighted routing across HF + Railway + Fly.io (configurable weights)
- [ ] Supabase read replica (EU region) for multi-region reads
- [ ] Upstash Global Redis for distributed rate limiting + session data
- [ ] Cloudflare R2 for file/artifact storage (multi-region by default)
- [ ] Per-region agent routing: EU users → EU backend → EU DB replica

**Migration readiness status:**
- ✅ Compute: standard Dockerfile, portable to any Docker host
- ✅ Database: Supabase PostgreSQL, any Postgres via `DATABASE_URL` env var
- ✅ Auth: Firebase (cloud-agnostic SDK)
- ✅ Payments: Stripe (cloud-agnostic)
- ✅ DNS/Gateway: CF Worker — backend URL is a config var, clients never change
- ⚠️ Rate limiter: in-memory (must move to Redis for multi-instance)
- ⚠️ Alembic: runs in lifespan (must move to CI for multi-instance)
- ⚠️ Embedding cache: in-memory (must move to Redis)

---

## Testing Mandate

**All changes MUST be tested backend AND frontend in parallel before marking complete.**
- Backend: direct API calls (httpx/curl) against staging
- Frontend: Playwright browser tests against staging UI
- Both must pass. No exceptions.

---

## Design Docs Index

| Date | Document | Status |
|------|----------|--------|
| 2026-02-27 | x402/OpenClaw payment design | Planned |
| 2026-02-28 | Real work demo design | Completed |
| 2026-03-05 | Task lifecycle UX design | Approved, not started |
| 2026-03-05 | Simplified onboarding design | Superseded |
| 2026-03-07 | Streamlined developer journey design | 9/10 complete |
| 2026-03-07 | Bug fixes progress | All verified |
| 2026-03-08 | 4 Pillars production-readiness | All complete |
| 2026-03-09 | Marketplace polish (docs, domain, feedback) | Complete |
| 2026-03-10 | Production launch + Stripe + Promptfoo agent | Complete |
| 2026-03-11 | Production hardening + live payments | Complete |
| 2026-03-12 | Developer payouts + payout safety | Complete |
| 2026-03-13 | Sidebar consolidation + workflows + schedules | Complete |
| 2026-03-17 | No-code agent builder design | Complete |
| 2026-03-17 | Langflow pool infrastructure plan | Complete |
| 2026-03-17 | Langflow iframe auth plan | Complete |
| 2026-03-17 | Publish/review flow plan | In progress |
| 2026-03-18 | Agent orchestration patterns design | Complete |
| 2026-03-18 | Agent orchestration patterns implementation plan | Complete |
| 2026-03-18 | Hybrid agents — local/on-device execution roadmap | Planned (5 phases) |
| 2026-03-18 | Resilience & multi-cloud readiness | Planned (3 tiers) |
| 2026-03-19 | Protocol adoption roadmap (AG-UI, A2UI, MCP, AP2, UCP) | Planned (5 phases) |
| 2026-03-19 | Compliance certification plan (SOC 2, GDPR, HIPAA) | Complete (64/64 resolved) |
| 2026-03-19 | Cookie & privacy compliance audit | Phases 1-2 + UX complete, Phase 3 remaining |
| 2026-03-19 | Agent submissions gap fixes | Complete (5 gaps fixed) |
| 2026-03-19 | E2E test plan — 37 pages, 120+ endpoints | Complete |
| 2026-03-20 | Health monitor fix — post-incident (18 gaps) | Complete (all 4 phases) |
| 2026-03-20 | Landing page redesign spec (search-first, 45% shorter) | Complete |
| 2026-03-21 | Admin platform control suite (10 pages) | Complete |
| 2026-03-21 | E2E test refresh (50/60 pass) | Complete |
| 2026-03-21 | Incident response procedure | Complete |
| 2026-03-21 | Data Processing Agreement (DPA) | Complete |
| 2026-03-21 | SOC 2 controls mapping (CC1-CC9 + supplemental) | Complete |
| 2026-03-21 | Penetration test report (51 tests, OWASP Top 10) | Complete (0 open findings) |
| 2026-03-21 | RBAC 3-tier enforcement + role management API + admin UI | Complete |
| 2026-03-21 | Multi-Channel Gateway Phase 1-2 implementation plan | Complete |
| 2026-03-21 | Mobile hero cards overflow fix + compact layout | Complete |
| 2026-03-22 | Channel & Customer Management design spec (v2, compliance-approved) | Complete |
| 2026-03-22 | Channel & Customer Management implementation plan (10 tasks) | Complete |
| 2026-03-22 | Gateway compliance audit (24 findings, all resolved) | Complete |
| 2026-03-22 | Gateway deployment + secrets + E2E verification | Complete |
| 2026-03-22 | CF Worker Gateway — Telegram E2E working (~10s response) | Complete |
| 2026-03-22 | Gateway task-status endpoint (gateway-authenticated polling) | Complete |
| 2026-03-22 | Platform integration guide (how to add Slack/Discord/WhatsApp) | Complete |
| 2026-03-22 | CF Worker Gateway compliance audit (12 findings, all resolved) | Complete |
| 2026-03-22 | Production deployment record (pre-deploy checklist, rollback plan) | Complete |
| 2026-03-22 | Auto webhook registration (browser→CF Worker→Telegram, zero manual steps) | Complete |
| 2026-03-22 | Production E2E: 3 agents tested (Design, Translator, Support) | Complete |
| 2026-03-22 | Production deployment record (72 commits, 106 audit findings resolved) | Complete |
