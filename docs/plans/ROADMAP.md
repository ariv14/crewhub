# CrewHub Development Roadmap

**Last updated:** 2026-03-10
**Staging:** marketplace-staging.aidigitalcrew.com | arimatch1-crewhub-staging.hf.space
**Production:** arimatch1/crewhub (HF Space)

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

### Marketplace Polish (Mar 9-10) — ON STAGING
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

---

## Tomorrow (Mar 11) — Production Deploy

### Pre-Deploy Checklist
- [ ] Verify `DEBUG=false` on production HF Space (`arimatch1/crewhub`)
- [ ] Set `DISCORD_FEEDBACK_WEBHOOK` secret on production HF Space
- [ ] Verify Cloudflare Worker routes `api.aidigitalcrew.com` → production Space
- [ ] Verify DNS CNAME for `api.aidigitalcrew.com` → Cloudflare
- [ ] Merge `staging` → `main` (`git checkout main && git merge staging && git push origin main`)
- [ ] Verify frontend deploy (Cloudflare Pages prod) succeeds
- [ ] Verify backend deploy (HF Spaces prod) succeeds
- [ ] Smoke test: landing page, docs, agents browse, feedback widget, search box

### Post-Deploy Verification
- [ ] `https://api.aidigitalcrew.com/health` returns healthy
- [ ] Feedback widget sends to Discord from production
- [ ] Docs page loads at production URL
- [ ] Swagger UI is NOT accessible on production (`/docs` returns 404)

---

## In Progress / Remaining

### Completed (this sprint)
- [x] Write E2E test for register-agent flow (detect → review → register → success)
- [x] Fix HF Space storage limit (>1GB, failing `upload_folder` deploys)
- [x] Agent activity tab / task logs per agent
- [x] Analytics dashboard for agent owners
- [x] Webhook logs viewer (with 90-day retention policy)
- [x] Version bumping UI (patch/minor/major)

### Near-Term (after production deploy)
- [ ] Activate Stripe payments (business verification, live mode keys)
- [ ] Pricing page — connect to real Stripe checkout
- [ ] Magic box onboarding for end users (Approach B from simplified-onboarding-design)
- [ ] Delegation accuracy analytics query (data captured, no reporting endpoint)

### Backlog
- [ ] x402/OpenClaw payment integration (design: `2026-02-27-x402-openclaw-design.md`)
- [ ] Task lifecycle UX enhancement (design: `2026-03-05-task-lifecycle-ux-design.md`)
- [ ] Inline skill editor
- [ ] Premium tier implementation (monthly credits, priority matching)
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
| 2026-03-11 | Production deploy | Planned |
