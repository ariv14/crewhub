# Activity Rings — Agent Status Visualization

## Overview

CSS-only animated rings around agent avatars driven by SSE live events. Shows agent activity state across three locations: marketplace cards, dashboard status board, and agent detail page.

## Component: `<ActivityRing>`

Wraps any avatar with concentric rings:
- **Outer ring** — pulses on SSE events for that agent, fades after 10s
- **Inner glow** — steady color by status (green=active, amber=working, red=error, gray=inactive)
- **Intensity** — pulse speed scales with event frequency (low=3s, medium=1.5s, high=0.8s)

Three sizes: `sm` (cards, 9x9), `md` (dashboard board, 10x10), `lg` (detail header, 14x14).

## Hook: `useAgentActivity`

- Subscribes to `/activity/stream` SSE endpoint
- Maintains `Map<agentId, { lastEvent, eventCount, timestamp }>`
- Exposes `getAgentActivity(agentId)` returning `{ isActive, intensity, lastEventType }`
- Events older than 10s age out (ring stops pulsing)
- Shared via `AgentActivityProvider` context in marketplace layout

## Locations

1. **Agent cards** (`/agents`) — wrap avatar in `ActivityRing(sm)`, pulse on events
2. **Dashboard** — new `AgentStatusBoard` widget: compact grid of `ActivityRing(md)` circles
3. **Agent detail** — wrap header avatar in `ActivityRing(lg)`, add "Last active: Xm ago"

## CSS Animations

Pure Tailwind + custom keyframes in globals.css:
- `ring-pulse` keyframe: opacity 0.4→1 + scale 1→1.08
- Speed classes: `.ring-pulse-low` (3s), `.ring-pulse-medium` (1.5s), `.ring-pulse-high` (0.8s)
- Status glow via box-shadow (green/amber/red/none)

## Graceful Degradation

- Unauthenticated: static glow only (no SSE, no pulse)
- SSE disconnected: rings fade to static within 10s
- Mobile: same rings, no layout change

## Files

| Action | File |
|--------|------|
| Create | `components/agents/activity-ring.tsx` |
| Create | `lib/hooks/use-agent-activity.ts` |
| Create | `components/agents/agent-status-board.tsx` |
| Modify | `components/agents/agent-card.tsx` |
| Modify | `components/agents/agent-detail-header.tsx` |
| Modify | `app/(marketplace)/dashboard/page.tsx` |
| Modify | `app/(marketplace)/layout.tsx` |
| Modify | `globals.css` |
