# CrewHub Development Roadmap

**Last updated:** 2026-03-18
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

### Stripe Dashboard Manual Steps (Pending)
- [ ] **Staging**: Enable Stripe Connect (test mode), add `account.updated` webhook event
- [ ] **Staging**: Remove 4 stale subscription webhook events
- [ ] **Production**: Remove 4 stale subscription webhook events (customer.subscription.*, invoice.payment_failed)
- [ ] **Production**: Enable Stripe Connect when ready for real developer payouts

---

## Current Sprint

### Near-Term
- [ ] Agent submissions/review flow (models + schemas created, UI in progress)
- [x] Run E2E tests for orchestration patterns on staging — 6/6 pass
- [x] Run E2E tests on production — 14/14 functional tests pass
- [x] Merge Team Mode into Workflows — complete
- [ ] Delegation accuracy analytics query (data captured, no reporting endpoint)
- [ ] Redis-backed embedding rate limiter (current: in-memory, single-process only)

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
