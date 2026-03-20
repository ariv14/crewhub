// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
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
  active: "",
  inactive: "",
  suspended: "glow-error",
  unavailable: "",
  working: "glow-working",
};

const DOT_COLORS: Record<AgentStatus, string> = {
  active: "bg-green-500",
  inactive: "bg-gray-400",
  suspended: "bg-red-500",
  unavailable: "bg-amber-500",
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
      {!activity?.isActive && (
        <span
          className={cn(
            "absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-background",
            DOT_COLORS[status],
          )}
        />
      )}
    </div>
  );
}
