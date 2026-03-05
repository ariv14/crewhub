# Task Lifecycle UX Enhancement — Design Doc

**Date:** 2026-03-05
**Status:** Approved
**Scope:** Task detail page overhaul + task list improvements + agent performance tracking

---

## Problem

The task detail page is functional but sparse. Users can't quickly assess task progress, agent output is displayed as raw text, and there's no way to evaluate agent reliability before or after delegating work.

## Design: Approach C — Dashboard-style Cards with Hero Stepper

Keep the 2-column layout (2/3 main + 1/3 sidebar). Add a top progress stepper, enhance each card, and add new capabilities.

---

## Part 1: Core UI Enhancements

### 1.1 Progress Stepper (new component: `TaskProgressStepper`)

Horizontal step indicator below the page header.

Steps (happy path): `Submitted` -> `Working` -> `Completed`

- Past steps: green checkmark
- Current step: highlighted with pulse animation
- Future steps: dimmed/grey circle
- Terminal states (`failed`, `canceled`, `rejected`): red X on the failing step
- `input_required`: orange pause icon on the working step
- Below each step: relative timestamp ("2m ago") if reached
- Right side: elapsed time since task creation

### 1.2 Agent Identity Card (enhanced Details sidebar)

Replace truncated UUID with:
- Agent name (`provider_agent_name`)
- Skill name as subtitle (`skill_name`)
- Link to agent detail page
- Credits/payment/latency info below

### 1.3 Better Artifact Display (enhanced `TaskArtifactsDisplay`)

- Markdown rendering via `react-markdown` + `remark-gfm` (new deps)
- Copy-to-clipboard button on each artifact
- Collapsible "Show raw text" toggle
- JSON artifacts: pretty-printed with syntax coloring
- Images: unchanged (already handled)

### 1.4 Richer Processing State (enhanced working banner)

Replace minimal "Agent is processing..." with:
- Animated indeterminate pulse/progress bar
- Live elapsed time counter (ticking every second via `useEffect` interval)
- Shown for `submitted` and `working` states

### 1.5 Message Thread Polish (enhanced `TaskMessageThread`)

- "You" instead of "user", agent name instead of "agent"
- Timestamps on each message
- Better visual distinction for user vs agent bubbles

---

## Part 2: Task Lifecycle Features

### 2.1 Task Retry

- "Retry" button on failed/canceled tasks
- Creates new task with same `provider_agent_id`, `skill_id`, and original message
- Navigates to the new task detail page

### 2.2 Task Duplicate ("Run Again")

- "Run Again" button on completed tasks
- Same as retry but for successful tasks (useful for recurring work)
- Pre-fills the create task form with same agent/skill/message

### 2.3 Live Status Polling

- `useTask` already supports `refetchInterval` — verify it polls while status is `submitted`/`working`
- Auto-stop polling when task reaches terminal state
- The progress stepper + elapsed timer update automatically as status changes

### 2.4 Cost Breakdown

- Show platform fee separately: "8 credits (incl. 0.8 platform fee)"
- Display in the Details card

---

## Part 3: Agent Performance Tracking

### 3.1 Agent Scorecard (on task detail sidebar)

Below the agent identity card, show:
- Success rate % (completed / total tasks)
- Average latency
- Average rating (stars)
- Total tasks completed

Data source: backend already tracks per-agent task counts, ratings, and latency. May need a new API endpoint or extend the existing agent detail response.

### 3.2 Reliability Badges (on agent cards in browse/search)

- "99% success" badge if success rate > 95%
- "Fast" badge if avg latency < 5s
- "Top rated" badge if avg rating > 4.5
- Displayed on `AgentSearchCard` in task creation page and agent browse page

### 3.3 Per-Skill Stats

- On agent detail page, show per-skill breakdown:
  - Avg latency, success rate, avg rating per skill
- Helps users pick the right skill when an agent has multiple

---

## New Dependencies

- `react-markdown` — markdown rendering
- `remark-gfm` — GitHub-flavored markdown (tables, strikethrough, etc.)

## Files to Create/Modify

### New components:
- `frontend/src/components/tasks/task-progress-stepper.tsx`

### Modified components:
- `frontend/src/app/(marketplace)/dashboard/tasks/[id]/task-detail-client.tsx` — layout restructure
- `frontend/src/components/tasks/task-artifacts-display.tsx` — markdown + copy + collapse
- `frontend/src/components/tasks/task-message-thread.tsx` — labels + timestamps
- `frontend/src/components/tasks/task-status-badge.tsx` — possibly add reliability badges

### New hooks/utils:
- `frontend/src/lib/hooks/use-elapsed-time.ts` — live elapsed timer hook
- Extend `useTask` for auto-polling behavior

### Backend (if needed for agent stats):
- Extend `GET /api/v1/agents/{id}` response with performance stats
- Or new endpoint `GET /api/v1/agents/{id}/stats`

### E2E tests:
- Update `frontend/e2e/task-creation.spec.ts` for new UI elements
- Add task detail lifecycle test

---

## Layout Reference

```
+---------------------------------------------------+
| <- Back to Tasks                                   |
| Task abc12345  [Completed]              [Cancel]   |
| Created 2h ago - Completed 1h ago                  |
+---------------------------------------------------+
| [v Submitted] === [v Working] === [* Completed]    |
|    2h ago           1h ago          1h ago          |
+------------------------------+--------------------+
|                              | Agent               |
|  Conversation                | Frontend Developer  |
|  +-------------------- You + | Engineering         |
|  | Summarize this...       | | * 4.2/5 - 12 tasks |
|  +-------------------------+ | [View Agent ->]     |
|  + Agent -----------------+  |                     |
|  | Here's the summary     |  | Details             |
|  +------------------------+  | Quoted: 10 credits  |
|                              | Charged: 8 credits  |
|  Output            [Copy]    | Fee: 0.8 credits    |
|  +------------------------+  | Payment: Credits    |
|  | Rendered markdown      |  | Latency: 1200ms    |
|  | content here...        |  |                     |
|  | [> Show raw]           |  | Timeline            |
|  +------------------------+  | v Submitted  2h ago |
|                              | v Working    1h ago |
|  [Retry] [Run Again]        | * Completed  1h ago |
|                              |                     |
|  * Rate this task            | Performance         |
|  *****                       | 98% success rate    |
|                              | Avg 1.2s latency    |
+------------------------------+--------------------+
```
