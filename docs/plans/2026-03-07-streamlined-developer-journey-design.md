# Streamlined Developer Journey — Design Doc

**Date:** 2026-03-07
**Status:** Approved
**Goal:** 1000 developers register agents on day 1. 4 steps, 30 seconds.

---

## The Journey

```
1. Homepage → "Register Your Agent"
2. Paste endpoint URL → auto-detect (no auth needed)
3. Sign in with Google → Review → Register
4. Agent detail page → agent is live
```

---

## Change 1: `/register-agent` Page

New dedicated page. No fork screen, no onboarding wrapper.

### Step 1 — Paste URL
- URL input + "Detect Agent" button
- Helper text: "We'll read your /.well-known/agent-card.json"
- Detect endpoint becomes public (IP rate limited, 10/min)
- No auth required at this step

### Step 2 — Sign In (conditional)
- Only shown if user is not authenticated
- Inline Google Sign-In button (not a redirect to /login)
- Skipped entirely if already signed in
- After sign-in, stays on same page — no navigation

### Step 3 — Review & Register
- Auto-filled from detection: name, description, version, category
- Skills shown as badges
- Pricing defaults: Open, 1 credit, Per Task (editable)
- "Register Agent" button → POST /agents/
- On success → redirect to /agents/{id} with toast

### Detect Endpoint Change
- Remove `get_current_user` dependency from `POST /agents/detect`
- Add IP-based rate limit (10 requests/minute) to prevent abuse
- Registration still requires auth (POST /agents/)

---

## Change 2: Dashboard Welcome State

Replace the entire `/onboarding` flow.

### When `onboarding_completed === false`:
- Dashboard page shows full-page welcome state (not a banner)
- Two cards: "Browse Agents" → /agents, "Register Your Agent" → /register-agent
- Clicking either card silently calls POST /auth/onboarding to set flag
- No redirect to /onboarding — dashboard always loads

### When `onboarding_completed === true`:
- Normal dashboard: stats, activity feed, agent status board

### Delete:
- `/onboarding` route and page
- `onboarding-wizard.tsx`
- `fork-screen.tsx`
- `dev-onboarding.tsx`
- All step components (step-welcome, step-api-keys, step-interests, step-recommended, step-try-agent, step-success)
- `e2e/dev-onboarding.spec.ts`
- Remove `router.replace("/onboarding")` redirect from dashboard

---

## Change 3: Agent Settings Page

New page at `/dashboard/agents/{id}` for agent owners.

### Three sections:

**Details (editable form):**
- Name, description, endpoint URL, version, category, pricing
- Save button → PUT /agents/{id}

**Re-detect:**
- "Re-detect from Agent Card" button
- Re-fetches /.well-known/agent-card.json from endpoint
- Shows diff of what changed (new skills, updated description, etc.)
- Confirm to apply changes

**Danger Zone:**
- Deactivate Agent — hides from marketplace, existing tasks complete
- Delete Agent — permanent, requires typing agent name to confirm

### Access:
- Owner-only (agent.owner_id === currentUser.id)
- Linked from agent detail page ("Manage Agent" button, visible to owner only)
- Linked from "My Agents" table (action column)

---

## Change 4: Landing Page

Replace current hero + features section.

### New layout:
- Heading: "The AI Agent Marketplace"
- Subheading: one-liner about CrewHub
- Two CTAs side by side:
  - "Browse Agents" → /agents
  - "Register Your Agent" → /register-agent
- Feature cards below (keep Agent Discovery, Verified, Payments)
- Remove "Get Started" button (replaced by the two CTAs)

---

## File Changes

| Action | File |
|--------|------|
| New | `frontend/src/app/(marketplace)/register-agent/page.tsx` |
| New | `frontend/src/app/(marketplace)/dashboard/agents/[id]/page.tsx` |
| New | `frontend/src/components/agents/agent-settings.tsx` |
| Modify | `frontend/src/app/(marketplace)/page.tsx` (landing) |
| Modify | `frontend/src/app/(marketplace)/dashboard/page.tsx` (welcome state) |
| Modify | `frontend/src/app/(marketplace)/agents/[id]/agent-detail-client.tsx` (owner link) |
| Modify | `frontend/src/app/(marketplace)/dashboard/agents/page.tsx` (settings link) |
| Modify | `src/api/detect.py` (public + IP rate limit) |
| Delete | `frontend/src/app/(marketplace)/onboarding/page.tsx` |
| Delete | `frontend/src/components/onboarding/*` (8 files) |
| Delete | `frontend/e2e/dev-onboarding.spec.ts` |

---

## Not Building (Week 2+)

- Activity tab / task logs per agent
- Version bumping UI (patch/minor/major buttons)
- Inline skill editor (re-detect covers this)
- Analytics dashboard
- Webhook logs
- Owner toolbar on public agent page (settings page handles it)

---

## Success Criteria

1. Developer with a deployed HF Space agent can register in under 30 seconds
2. No auth required until the register step
3. Post-registration: developer can edit agent details, re-detect skills, deactivate/delete
4. New users see welcome state on dashboard, not a multi-step wizard
5. Zero dead-end pages — every step leads somewhere useful
