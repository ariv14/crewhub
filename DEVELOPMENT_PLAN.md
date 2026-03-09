# CrewHub Development Plan — Post Production-Readiness

## Status: Phase 2 Complete, Phase 5 (Launch) Next (Mar 9, 2026)

### Completed
- **Production-Readiness** — All 4 pillars (Evals, Guardrails, Autonomy vs Control, User Behavior Anticipation)
  - Sprint 1: Circuit breaker, per-user spending limits, high-cost task approval, cancellation grace period, automated quality scoring
  - Sprint 2: Content moderation, abuse detection, delegation depth limits, offline handling, telemetry
  - Sprint 3: Eval trends dashboard, low-confidence suggestion guard, feedback loop UI
- **Phase 0A: Stripe Integration** — Stripe checkout with tiered credit packs (500/2K/5K/10K), webhook idempotency, pricing page, earnings display, nav link
- **Phase 0B: Multi-Provider LLM** — LiteLLM Router (Groq → Cerebras → SambaNova → Gemini), separate eval budget (Gemini Flash), deployed to all 9 HF Spaces
- **Phase 1: Landing Page Repositioning** — Hero rewrite ("One AI can't be the best at everything"), two action cards (Team Mode + Magic Box), builder banner CTA, live stats from API (`/analytics/public-stats`), three audience value props, features section, fully responsive (tested 390px/768px/1280px)
- **UX Fixes (Mar 9):**
  - Mobile hamburger menu now mirrors full sidebar (Overview, My Agents, Team, Import were missing)
  - Dashboard stat cards now clickable (Credits → credits page, Tasks → tasks page, Agents → agents page)
- **Phase 2: AgentCrew (Saved Teams)** — Full CRUD, inline execution, save from team page, clone, public sharing
  - Backend: model (`AgentCrew` + `AgentCrewMember`), schema, service, API (8 endpoints), migration 019
  - Frontend: list page (grid cards), detail page (edit with reorder, inline run with consolidated report), save dialog on team page
  - Infra: eager-loading fix, alembic migration moved to Python lifespan (fixed HF Spaces boot loop), Cloudflare `_redirects`
  - E2E tested: 10/10 scenarios pass (list, detail, edit, run, clone, delete, public, mobile nav)

56 agents across 9 divisions deployed. 3-tier verification battle-tested. Responsive UI verified. 230 tests passing.

---

## Phase 1: Positioning & Landing Page ✅ Done (Mar 9, 2026)

**Goal**: Make users "get it" in 5 seconds — CrewHub is NOT another chatbot, it's the marketplace where AI agents compete and collaborate.

**Delivered:**
- ✅ 1.1 Hero rewrite: "One AI can't be the best at everything." + gradient text
- ✅ 1.2 Elevated Team card (3-col prominence, 4 agent avatars E/D/T/M, "Try Team Mode" CTA)
- ✅ 1.3 Three audience value props (Users, Developers, A2A Agents) replacing "How It Works"
- ✅ 1.4 Live stats from `GET /analytics/public-stats` (agents, tasks, success rate, credits earned)
- ✅ Builder banner CTA: "List Your Agent, Start Earning" with shimmer effect
- ✅ Features section: Semantic Discovery, Verified & Governed, Credit-Based Billing
- ✅ Full mobile responsiveness (tested 390px, 768px, 1280px)
- ✅ Mobile hamburger menu: all sidebar items (Overview, My Agents, Team, Import, etc.)
- ✅ Dashboard stat cards: clickable with navigation to relevant pages

---

## Phase 2: Saved Teams + Hyper-Personalization (5 days)

**Goal**: Transform team mode from a one-shot demo into a reusable workflow.

### 2.1 Data Model (Backend)

**New file**: `src/models/saved_team.py`
```
SavedTeam
  ├── id: UUID (PK)
  ├── owner_id: UUID (FK → User)
  ├── name: str ("My Dev Crew")
  ├── description: str (nullable)
  ├── icon: str (emoji, nullable)
  ├── is_public: bool (default false)
  ├── default_task_template: str (nullable)
  ├── created_at / updated_at
  │
  └── members: SavedTeamMember[]
        ├── id: UUID (PK)
        ├── team_id: UUID (FK → SavedTeam)
        ├── agent_id: UUID (FK → Agent)
        ├── skill_id: UUID (FK → AgentSkill)
        ├── position: int (ordering, 0-indexed)
        ├── role_instruction: str (nullable, custom prompt)
        └── is_lead: bool (default false)
```

**New file**: `src/schemas/saved_team.py`
- `SavedTeamCreate` (name, description, members[])
- `SavedTeamUpdate` (partial update)
- `SavedTeamResponse` (full team with member details)
- `SavedTeamListResponse` (paginated list)
- `TeamMemberCreate` (agent_id, skill_id, position, role_instruction)

### 2.2 API Endpoints (Backend)

**New file**: `src/api/saved_teams.py`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/teams/` | Create saved team |
| GET | `/api/v1/teams/` | List user's saved teams |
| GET | `/api/v1/teams/{id}` | Get team detail |
| PUT | `/api/v1/teams/{id}` | Update team (name, members, order) |
| DELETE | `/api/v1/teams/{id}` | Delete saved team |
| POST | `/api/v1/teams/{id}/run` | Execute saved team with a task message |
| POST | `/api/v1/teams/{id}/clone` | Clone a public team to own profile |
| GET | `/api/v1/teams/public` | Browse public teams (paginated) |

### 2.3 Team Mode Integration (Frontend)

**Modify**: `frontend/src/app/(marketplace)/team/page.tsx`
- After team results arrive, show **"Save this team"** button
- Opens save modal: name, description, optional role instructions per agent
- Save calls `POST /api/v1/teams/`

**Modify**: `frontend/src/lib/hooks/use-tasks.ts` (or new `use-teams.ts`)
- `useSavedTeams()` — list user's teams
- `useSavedTeam(id)` — get single team
- `useCreateTeam()` — create mutation
- `useUpdateTeam()` — update mutation
- `useDeleteTeam()` — delete mutation
- `useRunTeam()` — execute saved team
- `useCloneTeam()` — clone public team

### 2.4 My Teams Dashboard Page (Frontend)

**New file**: `frontend/src/app/(marketplace)/dashboard/teams/page.tsx`
- Grid of saved team cards (responsive: 1 col mobile, 2 tablet, 3 desktop)
- Each card shows: name, icon, overlapping agent avatars, member count, last used date
- Click → team detail page
- Empty state: "No saved teams yet" + CTA to team mode
- Add to dashboard sidebar navigation

### 2.5 Team Detail/Edit Page (Frontend)

**New file**: `frontend/src/app/(marketplace)/dashboard/teams/[id]/page.tsx`

Features:
- **Header**: Team name (editable inline), description, icon picker
- **Agent list**: Draggable cards (drag-to-reorder via `position`)
  - Each card: agent avatar, name, skill name, verification badge
  - Expandable: role instruction textarea
  - Remove button (trash icon)
  - "Swap agent" button → opens agent picker modal
- **Add agent**: "+ Add Agent" button → search/select from marketplace
- **Default template**: Textarea for pre-filled task message
- **Actions**: "Run Team" (primary CTA), "Clone" (if public), "Delete" (danger)
- **Visibility toggle**: Private / Public switch

### 2.6 Team Execution with Personalization (Backend)

**Modify**: `frontend/src/app/(marketplace)/team/page.tsx` and team execution logic
- When running a saved team, pass `role_instruction` per agent
- Backend prepends `role_instruction` to the task message sent to each agent
- Agents execute in `position` order (lead agent first if `is_lead=true`)

### 2.7 Alembic Migration

**New file**: `alembic/versions/019_saved_teams.py`
- Create `saved_teams` and `saved_team_members` tables
- Foreign keys to `users`, `agents`, `agent_skills`

---

## Phase 3: Developer Experience (3 days)

**Goal**: Make it trivially easy for developers to build, deploy, and monetize agents.

### 3.1 Agent Fork/Clone Feature

**Modify**: Agent detail page (`agent-detail-client.tsx`)
- Add "Fork this Agent" button (visible to logged-in users)
- Forks agent config (name, description, skills, pricing) into a new draft agent
- Opens `/dashboard/agents/new` pre-filled with forked data
- User customizes prompt, endpoint, pricing → registers as their own agent

**Backend**: `POST /api/v1/agents/{id}/fork`
- Creates a new agent owned by current user, copies skills/pricing/description
- Sets `forked_from_id` field for attribution
- Status: `draft` (not active until user sets endpoint)

**Modify**: `src/models/agent.py` — Add `forked_from_id: Optional[UUID]`

### 3.2 Agent Earnings Dashboard

**New section** in `/dashboard/agents/[id]` (agent settings page):
- Total credits earned (sum of completed task charges)
- Credits this week / this month
- Tasks completed chart (reuse eval-trends-chart pattern)
- Top skills by usage

**Backend**: Add to `src/api/analytics.py`:
- `GET /api/v1/analytics/agent/{id}/earnings` — aggregated earnings data

### 3.3 One-Command Agent Scaffold (Stretch)

**New file**: `scripts/create-agent-template.py`
- Generates a ready-to-deploy agent project (Dockerfile, A2A handler, LiteLLM config)
- `python scripts/create-agent-template.py --name "My Agent" --skill "code-review"`
- Output: complete directory that deploys to HF Spaces

---

## Phase 4: Social & Viral (2 days)

**Goal**: Users share teams, agents get discovered organically.

### 4.1 Public Team Gallery

**New page**: `frontend/src/app/(marketplace)/teams/browse/page.tsx`
- Browse public saved teams created by other users
- Filter by category, sort by popularity (clone count)
- "Use this team" → clones to your profile
- Like "Spotify playlists but for AI agent teams"

### 4.2 Shareable Team Links

- Public teams get a shareable URL: `/teams/{id}`
- Open Graph meta tags for social preview (team name, agent avatars, description)
- "Share" button copies link

### 4.3 Agent Embed Widget (Stretch)

- Embeddable `<iframe>` or `<script>` tag for agent builders
- "Try this agent" widget on external sites → runs task via CrewHub API
- Attribution link back to marketplace

---

## Phase 5: Production Launch (1 day)

### 5.1 Pre-Launch Checklist
- [ ] Merge staging → main
- [ ] Run full E2E test suite against production
- [ ] Verify all 56 agents respond on production backend
- [ ] Verify credit system works end-to-end
- [ ] Verify Firebase auth on production domain
- [ ] Check Sentry error monitoring is active
- [ ] Verify rate limiter and circuit breaker thresholds
- [ ] SSL/HTTPS verified on all endpoints

### 5.2 Launch
- [ ] Deploy frontend to production Cloudflare Pages
- [ ] Deploy backend to production HF Space
- [ ] Smoke test: landing → search → team mode → task complete
- [ ] Monitor Sentry for first-hour errors

---

## Priority & Timeline Summary

| Phase | What | Effort | Impact | Status |
|-------|------|--------|--------|--------|
| **0A** | Stripe integration | 2 days | Critical | ✅ Done |
| **0B** | Multi-provider LLM | 1 day | Critical | ✅ Done |
| **1** | Landing page repositioning | 3 days | High — first impressions | ✅ Done |
| **UX** | Mobile nav + clickable cards | 0.5 days | Medium — usability | ✅ Done |
| **2** | Saved teams (AgentCrew) | 3 days | High — retention + stickiness | ✅ Done |
| **3** | Developer experience | 3 days | Medium — supply side growth | ⬜ Planned |
| **4** | Social & viral features | 2 days | Medium — organic distribution | ⬜ Planned |
| **5** | Production launch | 1 day | Critical — ship it | 🔜 Next |

**Remaining: ~11 days to full launch-ready product.**

### Recommended Order
1. ~~Phase 0A + 0B~~ ✅ Complete
2. ~~Phase 1~~ ✅ Complete
3. ~~Phase 2 (saved teams — AgentCrew)~~ ✅ Complete
4. **Phase 5 (ship to prod)** ← NOW
5. Phase 3 + 4 (developer experience + social — growth loop)

---

## Files Touched (Summary)

### New Files
| File | Phase |
|------|-------|
| `frontend/src/app/(marketplace)/pricing/page.tsx` | 0A |
| `src/core/llm_router.py` | 0B |
| `src/models/saved_team.py` | 2 |
| `src/schemas/saved_team.py` | 2 |
| `src/api/saved_teams.py` | 2 |
| `alembic/versions/019_saved_teams.py` | 2 |
| `frontend/src/app/(marketplace)/dashboard/teams/page.tsx` | 2 |
| `frontend/src/app/(marketplace)/dashboard/teams/[id]/page.tsx` | 2 |
| `frontend/src/lib/hooks/use-teams.ts` | 2 |
| `frontend/src/app/(marketplace)/teams/browse/page.tsx` | 4 |

### Modified Files
| File | Phase | Why |
|------|-------|-----|
| `src/api/credits.py` | 0A | Enable purchases in prod, earnings endpoint |
| `src/api/billing.py` | 0A | Tiered pricing, idempotency, verify endpoint |
| `src/config.py` | 0A+0B | Credit tiers, LLM provider chain, eval model |
| `frontend/.../dashboard/credits/page.tsx` | 0A | Purchase flow fix, earnings tab |
| `frontend/.../dashboard/settings/page.tsx` | 0A | Subscription management UI |
| `src/services/eval_service.py` | 0B | Separate eval model (Gemini Flash) |
| `demo_agents/agency/app.py` | 0B | Multi-provider fallback in agents |
| `frontend/src/app/(marketplace)/page.tsx` | 1 ✅ | Hero copy, two action cards, audience props, features |
| `frontend/src/app/(marketplace)/team/page.tsx` | 2 | "Save this team" button |
| `src/models/agent.py` | 3 | `forked_from_id` field |
| `src/api/analytics.py` | 3 | Earnings endpoint |
| `frontend/.../agents/[id]/agent-detail-client.tsx` | 3 | Fork button |
| `frontend/.../dashboard/agents/[id]/*` | 3 | Earnings section |
| `src/api/analytics.py` | 1 ✅ | Public stats endpoint (`/analytics/public-stats`) |
| `frontend/src/components/landing/live-stats.tsx` (new) | 1 ✅ | Client component for live stats with fallbacks |
| `frontend/src/lib/api/agents.ts` | 1 ✅ | PublicStats type + getPublicStats() |
| `frontend/src/components/layout/top-nav.tsx` | UX ✅ | Mobile hamburger menu mirrors full sidebar |
| `frontend/src/components/shared/stat-card.tsx` | UX ✅ | Optional href prop for clickable cards |
| `frontend/src/app/(marketplace)/dashboard/page.tsx` | UX ✅ | Stat cards linked to relevant pages |
