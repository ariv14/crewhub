# CrewHub Development Roadmap

**Last updated:** 2026-03-10
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
- [x] Stripe payments enabled (test mode)
  - [x] Credit packs: 500/$5, 2000/$18, 5000/$40, 10000/$70
  - [x] Premium subscription: $9/mo (unlimited embeddings, 500 credits/month)
  - [x] Webhook endpoint configured for production
  - [x] `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`, `STRIPE_CREDIT_PACKS`, `FRONTEND_URL` set on HF Space
- [x] Owner account funded with 10,000 credits for testing

### Known Issues (Production)
- `DEBUG=true` on production (required until PostgreSQL is configured — SQLite in use)
- Swagger docs exposed at `/docs` (low risk — all endpoints require auth)
- Data stored in SQLite inside container (lost on restart)

---

## Tomorrow (Mar 11) — Hardening & Testing

### Priority: Production Database
- [ ] Set up PostgreSQL on Supabase (free tier, always-on, 500 MB)
- [ ] Set `DATABASE_URL` on production HF Space
- [ ] Set `DEBUG=false` on production (enables all security checks)
- [ ] Verify Swagger docs hidden, WEBHOOK_SECRET enforced
- [ ] Run Alembic migrations against production DB
- [ ] Re-register all agents (SQLite data lost on switch)

### Priority: Stripe Live Mode
- [ ] Complete Stripe business verification (Singapore account)
- [ ] Replace test keys with live keys (`sk_live_...`, `pk_live_...`)
- [ ] Create live webhook endpoint + signing secret
- [ ] End-to-end payment test (credit pack + premium subscription)

### Priority: Test All Features
- [ ] Credit pack purchase flow (test card `4242...`)
- [ ] Premium subscription upgrade + verify unlimited embeddings
- [ ] Promptfoo agent: test all 4 skills via Try It panel
- [ ] Agency agents: test at least 3 divisions via Try It
- [ ] Team mode: multi-agent task
- [ ] Feedback widget → Discord
- [ ] Register new agent flow

### In Progress / Remaining

#### Completed (this sprint)
- [x] Write E2E test for register-agent flow (detect → review → register → success)
- [x] Fix HF Space storage limit (>1GB, failing `upload_folder` deploys)
- [x] Agent activity tab / task logs per agent
- [x] Analytics dashboard for agent owners
- [x] Webhook logs viewer (with 90-day retention policy)
- [x] Version bumping UI (patch/minor/major)
- [x] Stripe payments enabled (test mode) — credit packs + premium subscription
- [x] Promptfoo agent deployed with 4 skills
- [x] Production Firebase Auth (GitHub + Google)
- [x] All agents registered on production under owner account

#### Near-Term
- [ ] Magic box onboarding for end users (Approach B from simplified-onboarding-design)
- [ ] Delegation accuracy analytics query (data captured, no reporting endpoint)
- [ ] Redis-backed embedding rate limiter (current: in-memory, single-process only)

#### Backlog
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
| 2026-03-11 | Production hardening + live payments | Planned |
