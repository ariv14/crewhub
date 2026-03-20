# Landing Page Redesign — Design Spec

> **Date:** 2026-03-21
> **Status:** Approved
> **Scope:** Landing page hero redesign — search-first, side-by-side panels, 45% shorter
> **Expert Panel:** Chief Design Officer, End User, Developer, Growth/CRO Expert

---

## Overview

Redesign the CrewHub landing page based on findings from 4 expert reviewers. Core changes: make search the primary CTA, show both Find/Team panels simultaneously (no tabs), cut 3 redundant sections, reduce CTAs from 15 to 3.

---

## Changes

### 1. Search-First Hero

Move MagicBox search input directly under the headline. Demote "Get Started Free" and "Browse Agents" to secondary text links below the search box.

```
Hire AI agents that deliver in seconds.
The marketplace for specialist AI agents. Describe what you need — get results instantly.

[🔍 What do you need help with?                    ] [Find]
Try: Summarize a document · Review my code · Translate to Spanish

No account needed to search · Get Started Free · Browse Agents
```

### 2. Side-by-Side Panels (Replace Tabs)

Replace `HeroTabs` with two simultaneously visible panels in a 2-column grid.

**Left panel: Find an Agent** (contains MagicBox search — already shown above in hero)
- Shows search results inline when user types
- Suggestion cards with agent info

**Right panel: Build a Workflow**
- 3 compact pattern rows (not full cards):
  - `[icon] Run Steps in Order     Sequential multi-step    [→]`
  - `[icon] Reusable Pipelines     Nested workflows         [→]`
  - `[icon] Let AI Plan It         AI picks the agents      [→]`
- "Create Workflow →" CTA at bottom
- Each row: ~48px height, hover border highlight

Desktop: `grid grid-cols-1 lg:grid-cols-5 gap-6` (left 3 cols, right 2 cols)
Mobile: stacked vertically, search first

### 3. Quality-Only Social Proof

Remove stats strip (56 agents, 170 tasks — hurts trust at current scale).
Keep only quality signals inline under hero:

```
95% success rate · 3-8s avg response · Powered by Groq
```

Small text, `text-muted-foreground`, centered. No animation, no ticker.

### 4. Merged CTA Strip

Combine "Build My Agent" and "List Your Agent" into one split container:

```
┌─────────────────────────────┬──────────────────────────────┐
│ Build My Agent (5 credits)  │ List Your Agent (earn 90%)   │
│ Describe it, we build it    │ Register your A2A endpoint   │
│ [Build Now →]               │ [Register →]                 │
└─────────────────────────────┴──────────────────────────────┘
```

Single `rounded-xl border-2 border-primary/20` container. Desktop: 2 columns. Mobile: stacked inside same container.

### 5. Trending Agents

Keep as-is — 4 agent cards with horizontal scroll on mobile. This is real content that serves as social proof through demonstration.

### 6. Cut Sections

**Remove entirely:**
- "Three ways to use CrewHub" flow cards (content absorbed into hero panels)
- "Built for Everyone in the AI Ecosystem" audience cards (repeats hero)
- Feature cards (Semantic Discovery, Verified, Credit-Based) — move to /explore

### 7. New Page Structure

```
1. Hero: headline + search box + quality stats          (~350px)
2. Side-by-side: Search results | Workflow patterns     (~280px)
3. Merged CTA strip: Build | List                       (~120px)
4. Trending Agents (4 cards, carousel on mobile)        (~350px)
5. Footer                                               (~100px)

Total: ~1,200px (down from ~2,850px)
```

---

## File Changes

### Modify
- `frontend/src/app/(marketplace)/page.tsx` — restructure sections, remove 3 sections, inline quality stats, merge CTA strips
- `frontend/src/components/landing/hero-tabs.tsx` — replace tabs with side-by-side panels OR delete and inline into page.tsx
- `frontend/src/components/landing/social-proof.tsx` — reduce to quality-only inline stats or delete

### Keep unchanged
- `frontend/src/components/landing/magic-box.tsx` — works as-is, just moves to hero position
- `frontend/src/components/landing/trending-agents.tsx` — keep as-is

---

## Mobile (375px)

- Search box is the ONLY hero CTA (remove Get Started Free button on mobile)
- Workflow panel stacks below search
- Merged CTA strip stacks vertically inside one container
- Trending agents horizontal scroll carousel
- Target: ~1,400px total scroll depth on mobile
