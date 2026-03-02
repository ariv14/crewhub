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
