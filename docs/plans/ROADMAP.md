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

### Compliance Readiness Summary (as of Mar 21)

**Technical compliance: 64/64 findings resolved (100%). All critical, high, and medium issues fixed.**

Remaining items are documentation/process only:

| Item | Type | Status | Blocker? |
|------|------|--------|----------|
| Server-side consent logging (`POST /auth/consent`) | Code | Not built | No — client-side consent works, server-side is defense-in-depth |
| CORS `allow_methods=["*"]` | Code | Overly permissive | Low risk — restrict to GET/POST/PUT/DELETE/PATCH/OPTIONS |
| DPA template for enterprise customers | Document | Not created | SOC 2 auditor engagement blocker |
| Incident response / breach notification procedure | Document | Not created | SOC 2 auditor engagement blocker |
| SOC 2 controls mapping (CC1-CC9) | Document | Not created | Auditor engagement blocker |

**What an auditor would flag today:**
1. Missing incident response plan (required for SOC 2 CC7.4)
2. Missing DPA (required for GDPR Art. 28 when processing EU customer data)
3. `compliance.txt` claims SOC 2 Type II / GDPR certified / HIPAA assessed — **these certifications have not been obtained yet**. Update to "pursuing" or "aligned with" to avoid misrepresentation.

### Cookie & Privacy — Phase 3 (remaining)
- [ ] `POST /api/v1/auth/consent` endpoint — stores timestamp, version, IP
- [ ] Call from handleAccept() in posthog-provider
- [ ] Version the consent key (analytics_consent_v1.0)

### Multi-Channel Gateway (Mar 18) — DESIGNED, NOT YET IMPLEMENTED
- [x] Full design spec: `docs/superpowers/specs/2026-03-18-multi-channel-gateway-design.md`
- [x] 5 platforms (Slack, Discord, Telegram, WhatsApp, email), developer-pays model
- [x] Async callback pattern, 5 implementation phases
- [ ] Phase 1 implementation (next priority)

### Near-Term
- [ ] Delegation accuracy analytics query (data captured, no reporting endpoint)
- [ ] Redis-backed embedding rate limiter (current: in-memory, single-process only)
- [ ] CORS: restrict `allow_methods` to actual methods used (currently `["*"]`)
- [ ] Fix `compliance.txt` — change "has completed" / "is certified" to "pursuing" / "aligned with"

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
