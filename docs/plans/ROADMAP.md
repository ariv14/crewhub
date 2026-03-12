# CrewHub Development Roadmap

**Last updated:** 2026-03-12
**Staging:** marketplace-staging.aidigitalcrew.com | arimatch1-crewhub-staging.hf.space
**Production:** marketplace.aidigitalcrew.com | arimatch1/crewhub (HF Space)

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

### Stripe Dashboard Manual Steps (Pending)
- [ ] **Staging**: Enable Stripe Connect (test mode), add `account.updated` webhook event
- [ ] **Staging**: Remove 4 stale subscription webhook events
- [ ] **Production**: Remove 4 stale subscription webhook events (customer.subscription.*, invoice.payment_failed)
- [ ] **Production**: Enable Stripe Connect when ready for real developer payouts

---

## Current Sprint

### Near-Term
- [ ] Magic box onboarding for end users (Approach B from simplified-onboarding-design)
- [ ] Delegation accuracy analytics query (data captured, no reporting endpoint)
- [ ] Redis-backed embedding rate limiter (current: in-memory, single-process only)

### Backlog
- [ ] x402/OpenClaw payment integration (design: `2026-02-27-x402-openclaw-design.md`)
- [ ] Task lifecycle UX enhancement (design: `2026-03-05-task-lifecycle-ux-design.md`)
- [ ] Inline skill editor
- [ ] Multi-agent workflows / chaining

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
