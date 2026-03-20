# Landing Page UX Roadmap

**Created:** 2026-03-20
**Source:** Expert analysis by Product Owner + UX Designer agents
**Status:** In progress

---

## P0 — Critical Fixes

- [x] **P0-1: Magic Box starter chips auto-search** — clicking a suggestion chip should fill input AND trigger search automatically
  - File: `frontend/src/components/landing/magic-box.tsx`
  - Current: `onClick={() => setQuery(s)}` — just fills input
  - Fix: also call `handleSearch()` after setting query

- [x] **P0-2: Pass search query to "Browse all agents" link** — currently links to `/agents` with no `?q=` param, losing user's search context
  - File: `frontend/src/components/landing/magic-box.tsx`
  - Fix: change href to `/agents?q=${encodeURIComponent(query)}`

- [x] **P0-3: Add "5+ characters" hint to Magic Box** — Find button disabled with no explanation when query is 1-4 chars
  - File: `frontend/src/components/landing/magic-box.tsx`
  - Fix: show helper text below input when 1-4 chars entered

---

## P1 — UX Improvements

- [ ] **P1-1: Elevate Magic Box on homepage** — swap column proportions so Magic Box is larger (md:col-span-3) and AI Team card smaller (md:col-span-2)
  - File: `frontend/src/app/(marketplace)/page.tsx`

- [ ] **P1-2: Move stats bar closer to hero** — social proof most effective near the primary CTA
  - File: `frontend/src/app/(marketplace)/page.tsx`

- [ ] **P1-3: Consolidate "Three ways" + "Built for Everyone"** — these two sections repeat the same content, merge into one cleaner section
  - File: `frontend/src/app/(marketplace)/page.tsx`

- [ ] **P1-4: Add guided first-step prompt for empty workflows** — after creating a Manual/Hierarchical workflow with 0 steps, show inline "Add your first agent" prompt instead of requiring Edit button discovery
  - File: `frontend/src/app/(marketplace)/dashboard/workflows/[id]/workflow-detail-client.tsx`

- [ ] **P1-5: Simplify workflow pattern language for landing page** — replace jargon ("Hierarchical nested sub-workflows") with user-friendly descriptions ("Chain agents together", "Build complex pipelines", "Let AI plan for you")
  - File: `frontend/src/app/(marketplace)/page.tsx`

---

## P2 — Polish

- [ ] **P2-1: Reduce A2A persona prominence** — move "For AI Agents (A2A)" from first-class audience card to smaller note or separate page
  - File: `frontend/src/app/(marketplace)/page.tsx`

- [ ] **P2-2: Add loading skeleton for Trending Agents** — prevent layout shift when API is loading
  - File: `frontend/src/components/landing/trending-agents.tsx`

- [ ] **P2-3: Add pricing clarity higher on page** — "Most tasks cost 5-15 credits" near the "250 free credits" mention
  - File: `frontend/src/app/(marketplace)/page.tsx`

- [ ] **P2-4: Differentiate Hierarchical from Manual** — either implement sub-workflow nesting UI or consolidate with Manual
  - Decision needed: keep or merge?

- [ ] **P2-5: Add product demo/output example** — animated GIF or screenshot showing what an agent actually produces
  - Requires: asset creation, design decision

---

## Completed Today (2026-03-20)

- [x] Workflow detail page freeze fix (private workflows returned 404 for owner)
- [x] Error state handling on admin agent detail + agent settings pages
- [x] Trailing slashes on dashboard routes
- [x] Dashboard WelcomeState `<Link>` → `<a>` tags
- [x] Wrangler version pin for CF Pages deploy
- [x] Full E2E test suite: 397 tests, 62 journey steps — all passing
