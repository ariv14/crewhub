# Simplified Onboarding Design

**Status:** In progress — approaches proposed, awaiting decision on approach selection.

**Date:** 2026-03-05

---

## Problem

Current onboarding has 6 steps (welcome → API keys → interests → recommendations → try agent → success) before users get any value. API keys step confuses non-technical users. No developer-specific path exists. Agent registration requires a deployed endpoint but skips skills entirely.

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Audience | Both end users AND developers equally (Option C) | CrewHub serves both sides of the marketplace |
| End-user first value | "Magic box" (Option C1) — single text input, auto-select agent, show result | Zero concept learning, value in 10 seconds |
| Developer first value | "Bring your endpoint" (Option D2) — paste URL, auto-detect agent card | Quick win, no infrastructure needed, auto-fills skills/pricing from agent card |

## Approaches Under Consideration

### Approach A: "Fork-First"
Role picker on signup, then diverge into separate paths.

```
Sign up → "I want to..." → [Use agents] / [Build agents]
                                │                │
                         Magic text box     Paste endpoint URL
                         Auto-pick agent    Auto-detect agent card
                         Show result        Confirm & register
                         → Dashboard        → Dashboard
```

**Pros:** Clean separation, each path is 1-2 steps.
**Cons:** Forces binary choice. Some users are both.

### Approach B: "Magic Box First" (Recommended)
Everyone sees the magic box. Developer path is a secondary link.

```
Sign up → "What do you need help with?" → [text box]
                    │                            │
              [or: "I build agents →"]     Auto-pick agent
                    │                      Show result
              Paste endpoint URL           → Dashboard
              Auto-detect agent card
              Confirm & register
              → Dashboard
```

**Pros:** Strongest first impression. Optimizes for majority (users). Developers still have clear path. Users who experience value are more likely to also build agents.
**Cons:** Developer path is less prominent.

### Approach C: "Tabs"
Same screen, two tabs: "Use Agents" and "Build Agents".

```
Sign up → Onboarding screen with two tabs:
          ┌─────────────┬──────────────┐
          │  Use Agents  │ Build Agents │
          └─────────────┴──────────────┘

  [Use Agents tab]              [Build Agents tab]
  "What do you need?"           "Paste your agent URL"
  [text box]                    [url input]
  Auto-pick → result            Auto-detect → confirm
  → Dashboard                   → Dashboard
```

**Pros:** Both paths equally visible. Easy to switch.
**Cons:** More UI complexity.

## Pending Decisions

- [ ] Which approach (A, B, or C)?
- [ ] What happens if no agent matches the magic box query?
- [ ] Should we keep any existing onboarding steps (interests, API keys) as optional post-onboarding?
- [ ] Agent card auto-detection: what if `/.well-known/agent-card.json` is missing or malformed?
- [ ] Should the magic box use the existing `POST /api/v1/tasks/suggest` endpoint or a new one?

## Current Onboarding (Being Replaced)

6 steps, all mandatory before dashboard access:

1. Welcome — enter name
2. API Keys — OpenAI/Gemini keys (confusing for non-technical users)
3. Interests — pick categories (no context yet)
4. Recommended — show agents by interest
5. Try Agent — live task execution
6. Success — redirect to dashboard

## Key Technical Context

- Auto-delegation already exists: `POST /api/v1/tasks/suggest` returns ranked (agent, skill) suggestions
- Agent cards served at `GET /.well-known/agent-card.json` contain name, description, skills, pricing
- Current onboarding backend: `POST /auth/onboarding` stores name + interests, sets `onboarding_completed=true`
- Dashboard blocks access if `onboarding_completed=false`
- Try Agent panel (`try-agent-panel.tsx`) already creates real tasks and shows results inline
