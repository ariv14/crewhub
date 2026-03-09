# CrewHub Roadmap

## Status: Ready to Ship — Production Launch This Week (Mar 9, 2026)

### What We've Built
- **56 AI agents** across 9 divisions, 3-tier verification, multi-provider LLM routing
- **Team Mode** — multi-agent collaboration on a single task (the core differentiator)
- **Saved Crews** — reusable agent teams with inline execution, clone, public sharing
- **Credit Economy** — Stripe checkout (4 tiers), per-task billing, developer earnings
- **Production Guardrails** — circuit breaker, spending limits, content moderation, abuse detection, eval scoring
- **Auth** — Google + GitHub OAuth (Firebase), API key auth for agents
- **Landing Page** — "One AI can't be the best at everything" positioning, live stats, responsive

230 tests passing. Staging fully deployed and battle-tested.

---

## Phase 5: Ship to Production (This Week)

**Goal**: Get live on production domain. Stop building, start learning.

### 5.1 Pre-Launch
- [ ] Merge staging → main
- [ ] Run full E2E test suite against production
- [ ] Verify all 56 agents respond on production backend
- [ ] Verify credit system end-to-end (Stripe test → live mode)
- [ ] Verify Firebase auth on production domain (Google + GitHub)
- [ ] Check Sentry error monitoring active
- [ ] SSL/HTTPS on all endpoints

### 5.2 Deploy
- [ ] Deploy backend to production HF Space (`arimatch1/crewhub`)
- [ ] Deploy frontend to production Cloudflare Pages (`crewhub-marketplace`)
- [ ] Smoke test: landing → sign in → team mode → task complete → credits deducted
- [ ] Enable GitHub OAuth on production Firebase project (`ai-digital-crew`)

### 5.3 Analytics (Day 1)
- [ ] Add PostHog or Google Analytics to frontend
- [ ] Track: sign-ups, team mode usage, task completions, credit purchases
- [ ] Set up Sentry alerts for error spikes

---

## Phase 6: First 10 Users (Week 1-2 Post-Launch)

**Goal**: Get 10 real humans using CrewHub and learn what they actually want.

### 6.1 Distribution (Zero Budget)
- [ ] Record 60-second demo video: team mode solving a real task (3 agents, one prompt)
- [ ] Post on: HackerNews (Show HN), Reddit (r/artificial, r/SideProject), AI Twitter/X
- [ ] Share in Discord communities: LangChain, CrewAI, AutoGen, AI builders
- [ ] Personal outreach: 20 people who build with AI — DM with demo link

### 6.2 Onboarding Optimization
- [ ] First-time user gets 100 free credits (already implemented)
- [ ] Guided first task: pre-filled "Try Team Mode" with 3 suggested agents
- [ ] Success screen after first completed task → "Save this crew" CTA

### 6.3 User Interviews
- [ ] Talk to every early user (Calendly link on dashboard?)
- [ ] Key questions: What did you try? What broke? Would you pay? For what use case?
- [ ] Document patterns: which agents get used, which crews get saved

---

## Phase 7: Pick a Wedge (Week 3-4)

**Goal**: Based on user data, double down on one use case.

### Candidate Wedges

| Wedge | Target User | Why It Might Work |
|-------|------------|-------------------|
| **AI Code Review Crew** | Solo developers | "3 specialized reviewers in one click" — high frequency, clear value |
| **Content Team** | Marketers / writers | "5 AI perspectives on your blog post" — team mode is the moat |
| **Client Deliverables** | Agencies / freelancers | "Automate repetitive reports with saved crews" — high willingness to pay |

### Actions After Picking
- [ ] Rewrite landing page hero for the chosen wedge
- [ ] Build 2-3 pre-made crews optimized for that use case
- [ ] Create a "template gallery" of starter crews (replaces generic public gallery)
- [ ] Write one case study showing before/after

---

## Phase 8: Supply Side — Developer Growth (Week 5-6)

**Goal**: Other developers list agents on CrewHub. This is the real moat.

### 8.1 Agent Fork/Clone
- "Fork this Agent" button on any agent detail page
- Copies config into a new draft → developer customizes prompt + endpoint
- `forked_from_id` for attribution chain
- Backend: `POST /api/v1/agents/{id}/fork`

### 8.2 Agent Earnings Dashboard
- Per-agent: total credits earned, tasks completed, top skills
- Developer motivation: "Your agent earned 2,400 credits this month"
- Backend: `GET /api/v1/analytics/agent/{id}/earnings`

### 8.3 One-Command Agent Scaffold
- `python scripts/create-agent-template.py --name "My Agent" --skill "code-review"`
- Generates: Dockerfile, A2A handler, LiteLLM config → deploy to HF Spaces in minutes
- Lower the barrier to zero for listing an agent

---

## Phase 9: Viral Loops (Week 7-8)

**Goal**: Users bring other users. Crews are the sharing mechanism.

### 9.1 Public Crew Gallery
- Browse public crews by category, sort by popularity (clone count)
- "Use this crew" → clones to your profile
- Like "Spotify playlists but for AI agent teams"

### 9.2 Shareable Crew Links
- Public crews get a URL: `/crews/{id}` with OG meta tags
- "Share" button copies link
- Social preview: crew name, agent avatars, description

### 9.3 Agent Embed Widget (Stretch)
- Embeddable `<script>` tag for agent builders' websites
- "Try this agent" → runs via CrewHub API → attribution link back

---

## Key Metrics to Track

| Metric | Target (Month 1) | Why It Matters |
|--------|-------------------|----------------|
| Sign-ups | 100 | Basic interest signal |
| Users who complete 1 task | 30 | Activation — they "got it" |
| Users who complete 5+ tasks | 10 | Retention — real value |
| Crews saved | 20 | Stickiness — workflow adoption |
| Credit purchases | 5 | Willingness to pay |
| Agents listed by others | 3 | Supply side — marketplace flywheel |

---

## What We're NOT Doing (Yet)

- Mobile app — web-first, responsive is enough
- Enterprise features — no SSO, no team billing, no SLA
- Self-hosted — SaaS only
- Paid marketing — organic + community first
- Scale optimization — we need 10 users, not 10,000

---

## Completed Work (Reference)

| Phase | What | Status |
|-------|------|--------|
| **Production-Readiness** | 4 pillars: Evals, Guardrails, Autonomy vs Control, User Behavior | ✅ Done |
| **0A** | Stripe integration (4 credit tiers, webhook idempotency) | ✅ Done |
| **0B** | Multi-provider LLM (Groq → Cerebras → SambaNova → Gemini) | ✅ Done |
| **1** | Landing page repositioning + responsive | ✅ Done |
| **UX** | Mobile nav + clickable dashboard cards | ✅ Done |
| **2** | Saved Teams / AgentCrew (full CRUD + inline execution) | ✅ Done |
| **Auth** | GitHub OAuth login alongside Google | ✅ Done |

### Files Touched (Completed Phases)

**New Files:**
| File | Phase |
|------|-------|
| `frontend/src/app/(marketplace)/pricing/page.tsx` | 0A |
| `src/core/llm_router.py` | 0B |
| `src/models/crew.py` | 2 |
| `src/schemas/crew.py` | 2 |
| `src/api/crews.py` | 2 |
| `src/services/crew_service.py` | 2 |
| `alembic/versions/019_agent_crews.py` | 2 |
| `frontend/src/app/(marketplace)/dashboard/crews/page.tsx` | 2 |
| `frontend/src/app/(marketplace)/dashboard/crews/[id]/page.tsx` | 2 |
| `frontend/src/app/(marketplace)/dashboard/crews/[id]/crew-detail-client.tsx` | 2 |
| `frontend/src/lib/hooks/use-crews.ts` | 2 |

**Modified Files:**
| File | Phase | Why |
|------|-------|-----|
| `src/api/credits.py` | 0A | Purchases, earnings endpoint |
| `src/api/billing.py` | 0A | Tiered pricing, idempotency |
| `src/config.py` | 0A+0B | Credit tiers, LLM provider chain |
| `frontend/.../dashboard/credits/page.tsx` | 0A | Purchase flow, earnings tab |
| `src/services/eval_service.py` | 0B | Separate eval model (Gemini Flash) |
| `demo_agents/agency/division_agent.py` | 0B | Multi-provider fallback |
| `frontend/src/app/(marketplace)/page.tsx` | 1 | Hero, action cards, stats, features |
| `frontend/src/components/landing/live-stats.tsx` | 1 | Live stats from API |
| `frontend/src/app/(marketplace)/team/page.tsx` | 2 | "Save as Crew" dialog |
| `frontend/src/components/layout/user-sidebar.tsx` | 2 | My Crews nav item |
| `frontend/src/components/layout/top-nav.tsx` | 2+UX | Mobile nav, crews link |
| `frontend/src/lib/auth-context.tsx` | Auth | GithubAuthProvider |
| `frontend/src/app/(auth)/login/page.tsx` | Auth | GitHub sign-in button |
| `src/api/auth.py` | Auth | firebase_uid-first lookup, private-email fallback |
| `src/main.py` | Infra | Alembic in lifespan, crews router |
| `Dockerfile.hf` | Infra | Simplified CMD |
| `frontend/public/_redirects` | Infra | Crews rewrite rule |
