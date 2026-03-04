# Activity Rings Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add CSS-only animated rings around agent avatars that pulse on live SSE events, across marketplace cards, dashboard, and agent detail pages.

**Architecture:** A shared React context (`AgentActivityProvider`) subscribes to the existing SSE `/activity/stream` endpoint and maintains a per-agent activity map. A reusable `<ActivityRing>` wrapper component reads from this context to render concentric CSS rings. Three integration points: agent cards, dashboard status board, agent detail header.

**Tech Stack:** React context + hooks, Tailwind CSS custom keyframes, existing SSE infrastructure.

---

### Task 1: Add CSS keyframes for ring-pulse animation

**Files:**
- Modify: `src/app/globals.css`

**Step 1: Add the keyframes and utility classes**

Append to `globals.css` after the `@layer base` block:

```css
/* Activity ring animations */
@keyframes ring-pulse {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.08); }
}

.ring-pulse-low { animation: ring-pulse 3s ease-in-out infinite; }
.ring-pulse-medium { animation: ring-pulse 1.5s ease-in-out infinite; }
.ring-pulse-high { animation: ring-pulse 0.8s ease-in-out infinite; }

.glow-active { box-shadow: 0 0 8px 2px rgba(34, 197, 94, 0.35); }
.glow-working { box-shadow: 0 0 8px 2px rgba(245, 158, 11, 0.35); }
.glow-error { box-shadow: 0 0 8px 2px rgba(239, 68, 68, 0.35); }
.glow-inactive { box-shadow: none; }
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds, no CSS errors.

**Step 3: Commit**

```bash
git add src/app/globals.css
git commit -m "feat: add ring-pulse CSS keyframes for activity rings"
```

---

### Task 2: Create `useAgentActivity` hook and context provider

**Files:**
- Create: `src/lib/hooks/use-agent-activity.ts`

**Step 1: Write the hook and provider**

```typescript
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { API_V1 } from "@/lib/constants";

type Intensity = "low" | "medium" | "high";

interface AgentActivity {
  lastEventType: string;
  timestamp: number;
  eventCount: number;
}

interface AgentActivityContextValue {
  getActivity: (agentId: string) => {
    isActive: boolean;
    intensity: Intensity;
    lastEventType: string;
  } | null;
  connected: boolean;
}

const AgentActivityContext = createContext<AgentActivityContextValue>({
  getActivity: () => null,
  connected: false,
});

export function useAgentActivity() {
  return useContext(AgentActivityContext);
}

const ACTIVE_WINDOW_MS = 10_000; // 10 seconds
const INTENSITY_WINDOW_MS = 30_000; // 30 seconds for counting events

function computeIntensity(count: number): Intensity {
  if (count >= 5) return "high";
  if (count >= 2) return "medium";
  return "low";
}

export function AgentActivityProvider({ children }: { children: ReactNode }) {
  const activityMap = useRef(new Map<string, AgentActivity>());
  const [, setTick] = useState(0); // force re-renders on update
  const [connected, setConnected] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const retryCount = useRef(0);
  const retryDelay = useRef(1000);

  const processEvent = useCallback(
    (agentId: string, eventType: string) => {
      const now = Date.now();
      const existing = activityMap.current.get(agentId);

      if (existing && now - existing.timestamp < INTENSITY_WINDOW_MS) {
        existing.lastEventType = eventType;
        existing.timestamp = now;
        existing.eventCount += 1;
      } else {
        activityMap.current.set(agentId, {
          lastEventType: eventType,
          timestamp: now,
          eventCount: 1,
        });
      }
      setTick((t) => t + 1);
    },
    [],
  );

  // Extract agent ID from SSE events
  const handleSSEEvent = useCallback(
    (data: Record<string, unknown>) => {
      const eventType = (data.type as string) ?? "";
      const agentId =
        (data.provider_agent_id as string) ?? (data.agent_id as string);
      if (agentId) {
        processEvent(agentId, eventType);
      }
    },
    [processEvent],
  );

  // SSE connection (reuses same pattern as use-activity-feed.ts)
  const connect = useCallback(() => {
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("auth_token")
        : null;
    if (!token) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    (async () => {
      try {
        const res = await fetch(`${API_V1}/activity/stream`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });

        if (!res.ok || !res.body) throw new Error(`SSE ${res.status}`);

        setConnected(true);
        retryCount.current = 0;
        retryDelay.current = 1000;

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          let currentEvent = "";
          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              const raw = line.slice(5).trim();
              if (raw) {
                try {
                  const data = JSON.parse(raw) as Record<string, unknown>;
                  if (currentEvent) data.type = currentEvent;
                  handleSSEEvent(data);
                } catch {
                  /* ignore parse errors */
                }
              }
              currentEvent = "";
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return;
      } finally {
        if (!controller.signal.aborted) {
          setConnected(false);
          retryCount.current += 1;
          if (retryCount.current > 5) return;
          const delay = Math.min(retryDelay.current, 30000);
          retryDelay.current = delay * 2;
          setTimeout(connect, delay);
        }
      }
    })();

    return () => {
      controller.abort();
      setConnected(false);
    };
  }, [handleSSEEvent]);

  useEffect(() => {
    const cleanup = connect();
    return () => cleanup?.();
  }, [connect]);

  // Periodic cleanup of stale entries (every 5s)
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      let changed = false;
      for (const [id, entry] of activityMap.current) {
        if (now - entry.timestamp > INTENSITY_WINDOW_MS) {
          activityMap.current.delete(id);
          changed = true;
        }
      }
      if (changed) setTick((t) => t + 1);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const getActivity = useCallback(
    (agentId: string) => {
      const entry = activityMap.current.get(agentId);
      if (!entry) return null;

      const age = Date.now() - entry.timestamp;
      if (age > ACTIVE_WINDOW_MS) {
        return null; // no longer "active" — ring stops pulsing
      }

      return {
        isActive: true,
        intensity: computeIntensity(entry.eventCount),
        lastEventType: entry.lastEventType,
      };
    },
    [],
  );

  return (
    <AgentActivityContext.Provider value={{ getActivity, connected }}>
      {children}
    </AgentActivityContext.Provider>
  );
}
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 3: Commit**

```bash
git add src/lib/hooks/use-agent-activity.ts
git commit -m "feat: add useAgentActivity hook with SSE-driven per-agent state"
```

---

### Task 3: Create `<ActivityRing>` component

**Files:**
- Create: `src/components/agents/activity-ring.tsx`

**Step 1: Write the component**

```typescript
"use client";

import { cn } from "@/lib/utils";
import { useAgentActivity } from "@/lib/hooks/use-agent-activity";
import type { AgentStatus } from "@/types/agent";

interface ActivityRingProps {
  agentId: string;
  status: AgentStatus;
  size?: "sm" | "md" | "lg";
  children: React.ReactNode;
}

const SIZE_CLASSES = {
  sm: "p-[3px]",
  md: "p-1",
  lg: "p-1.5",
} as const;

const GLOW_CLASSES: Record<AgentStatus | "working", string> = {
  active: "glow-active",
  inactive: "glow-inactive",
  suspended: "glow-error",
  working: "glow-working",
};

const RING_COLORS: Record<string, string> = {
  task_created: "border-blue-400/60",
  task_completed: "border-green-400/60",
  task_failed: "border-red-400/60",
  agent_registered: "border-purple-400/60",
  credit_transaction: "border-amber-400/60",
};

const INTENSITY_CLASSES = {
  low: "ring-pulse-low",
  medium: "ring-pulse-medium",
  high: "ring-pulse-high",
} as const;

export function ActivityRing({
  agentId,
  status,
  size = "sm",
  children,
}: ActivityRingProps) {
  const { getActivity } = useAgentActivity();
  const activity = getActivity(agentId);

  const glowClass = activity?.isActive
    ? GLOW_CLASSES.working
    : GLOW_CLASSES[status];

  return (
    <div
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center rounded-full",
        SIZE_CLASSES[size],
        glowClass,
      )}
    >
      {/* Outer pulse ring */}
      {activity?.isActive && (
        <span
          className={cn(
            "absolute inset-0 rounded-full border-2",
            RING_COLORS[activity.lastEventType] ?? "border-green-400/60",
            INTENSITY_CLASSES[activity.intensity],
          )}
        />
      )}
      {children}
    </div>
  );
}
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 3: Commit**

```bash
git add src/components/agents/activity-ring.tsx
git commit -m "feat: add ActivityRing component with pulse and glow states"
```

---

### Task 4: Wire `AgentActivityProvider` into marketplace layout

**Files:**
- Modify: `src/app/(marketplace)/layout.tsx`

**Step 1: Add the provider**

Current layout (lines 1-15):
```tsx
import { TopNav } from "@/components/layout/top-nav";

export default function MarketplaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <TopNav />
      <main className="flex-1">{children}</main>
    </div>
  );
}
```

Change to:
```tsx
import { TopNav } from "@/components/layout/top-nav";
import { AgentActivityProvider } from "@/lib/hooks/use-agent-activity";

export default function MarketplaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <AgentActivityProvider>
      <div className="flex min-h-screen flex-col">
        <TopNav />
        <main className="flex-1">{children}</main>
      </div>
    </AgentActivityProvider>
  );
}
```

Note: `AgentActivityProvider` uses `"use client"` so the layout becomes a client boundary. This is fine — the `(marketplace)` layout already renders client components (`TopNav`).

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 3: Commit**

```bash
git add src/app/\(marketplace\)/layout.tsx
git commit -m "feat: wrap marketplace layout in AgentActivityProvider"
```

---

### Task 5: Integrate ActivityRing into agent cards

**Files:**
- Modify: `src/components/agents/agent-card.tsx`

**Step 1: Add imports and wrap Avatar**

Add imports at top:
```typescript
import { ActivityRing } from "@/components/agents/activity-ring";
```

Replace the Avatar block (lines 27-32):
```tsx
<Avatar className="h-9 w-9 shrink-0">
  <AvatarImage src={agent.avatar_url ?? undefined} alt={agent.name} />
  <AvatarFallback className="text-xs font-medium">
    {agent.name.charAt(0).toUpperCase()}
  </AvatarFallback>
</Avatar>
```

With:
```tsx
<ActivityRing agentId={agent.id} status={agent.status} size="sm">
  <Avatar className="h-9 w-9 shrink-0">
    <AvatarImage src={agent.avatar_url ?? undefined} alt={agent.name} />
    <AvatarFallback className="text-xs font-medium">
      {agent.name.charAt(0).toUpperCase()}
    </AvatarFallback>
  </Avatar>
</ActivityRing>
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 3: Commit**

```bash
git add src/components/agents/agent-card.tsx
git commit -m "feat: add activity ring to agent cards"
```

---

### Task 6: Integrate ActivityRing into agent detail header

**Files:**
- Modify: `src/components/agents/agent-detail-header.tsx`

**Step 1: Add imports and wrap Avatar**

Add import:
```typescript
import { ActivityRing } from "@/components/agents/activity-ring";
```

Replace the Avatar block (lines 34-39):
```tsx
<Avatar className="h-14 w-14 shrink-0">
  <AvatarImage src={agent.avatar_url ?? undefined} alt={agent.name} />
  <AvatarFallback className="text-lg font-semibold">
    {agent.name.charAt(0).toUpperCase()}
  </AvatarFallback>
</Avatar>
```

With:
```tsx
<ActivityRing agentId={agent.id} status={agent.status} size="lg">
  <Avatar className="h-14 w-14 shrink-0">
    <AvatarImage src={agent.avatar_url ?? undefined} alt={agent.name} />
    <AvatarFallback className="text-lg font-semibold">
      {agent.name.charAt(0).toUpperCase()}
    </AvatarFallback>
  </Avatar>
</ActivityRing>
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 3: Commit**

```bash
git add src/components/agents/agent-detail-header.tsx
git commit -m "feat: add activity ring to agent detail header"
```

---

### Task 7: Create AgentStatusBoard dashboard widget

**Files:**
- Create: `src/components/agents/agent-status-board.tsx`
- Modify: `src/app/(marketplace)/dashboard/page.tsx`

**Step 1: Write the status board component**

```typescript
"use client";

import { Bot } from "lucide-react";
import Link from "next/link";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ActivityRing } from "@/components/agents/activity-ring";
import { useAgentActivity } from "@/lib/hooks/use-agent-activity";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { Agent } from "@/types/agent";

interface AgentStatusBoardProps {
  agents: Agent[];
}

export function AgentStatusBoard({ agents }: AgentStatusBoardProps) {
  const { connected } = useAgentActivity();

  if (agents.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Agent Status</CardTitle>
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              connected ? "bg-green-400" : "bg-muted-foreground",
            )}
            title={connected ? "Live" : "Offline"}
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-4">
          {agents.map((agent) => (
            <Link
              key={agent.id}
              href={ROUTES.agentDetail(agent.id)}
              className="group flex flex-col items-center gap-1.5"
              title={agent.name}
            >
              <ActivityRing
                agentId={agent.id}
                status={agent.status}
                size="md"
              >
                <Avatar className="h-10 w-10">
                  <AvatarImage
                    src={agent.avatar_url ?? undefined}
                    alt={agent.name}
                  />
                  <AvatarFallback className="text-sm font-medium">
                    {agent.name.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
              </ActivityRing>
              <span className="max-w-[4rem] truncate text-xs text-muted-foreground group-hover:text-foreground">
                {agent.name.split(" ")[0]}
              </span>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Add AgentStatusBoard to the dashboard page**

In `src/app/(marketplace)/dashboard/page.tsx`, add import:
```typescript
import { AgentStatusBoard } from "@/components/agents/agent-status-board";
```

Add a second `useAgents` call (without owner filter) to get all platform agents for the status board. After the `<ActivityFeed />` (line 83), add:

```tsx
<AgentStatusBoard agents={allAgents?.agents ?? []} />
```

And add the hook at the top of the component (after existing hooks):
```typescript
const { data: allAgents } = useAgents({ per_page: 20 });
```

**Step 3: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 4: Commit**

```bash
git add src/components/agents/agent-status-board.tsx src/app/\(marketplace\)/dashboard/page.tsx
git commit -m "feat: add AgentStatusBoard dashboard widget with activity rings"
```

---

### Task 8: Visual verification and final commit

**Step 1: Build and verify**

Run: `cd frontend && npx next build 2>&1 | tail -10`
Expected: Build succeeds with no errors.

**Step 2: Verify all files are committed**

Run: `git status`
Expected: Clean working tree.

**Step 3: Push to staging**

```bash
git push origin staging
```

---

## File Summary

| # | Action | File | Description |
|---|--------|------|-------------|
| 1 | Modify | `src/app/globals.css` | ring-pulse keyframes + glow utilities |
| 2 | Create | `src/lib/hooks/use-agent-activity.ts` | SSE-driven per-agent activity context |
| 3 | Create | `src/components/agents/activity-ring.tsx` | Reusable ring wrapper component |
| 4 | Modify | `src/app/(marketplace)/layout.tsx` | Wrap in AgentActivityProvider |
| 5 | Modify | `src/components/agents/agent-card.tsx` | Wrap avatar in ActivityRing(sm) |
| 6 | Modify | `src/components/agents/agent-detail-header.tsx` | Wrap avatar in ActivityRing(lg) |
| 7 | Create | `src/components/agents/agent-status-board.tsx` | Dashboard status board widget |
| 7 | Modify | `src/app/(marketplace)/dashboard/page.tsx` | Add AgentStatusBoard |
| 8 | — | Push | Deploy to staging |
