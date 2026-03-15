// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { Area, AreaChart } from "recharts";
import { useAgentStats } from "@/lib/hooks/use-agents";

interface AgentSparklineProps {
  agentId: string;
}

export function AgentSparkline({ agentId }: AgentSparklineProps) {
  const { data } = useAgentStats(agentId);

  const points = data?.daily_tasks ?? [];
  // Show a flat line if no data
  const chartData = points.length > 0 ? points : [{ date: "", count: 0 }, { date: "", count: 0 }];

  return (
    <div className="h-8 w-20">
      <AreaChart width={80} height={32} data={chartData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id={`spark-${agentId}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="count"
          stroke="hsl(var(--primary))"
          strokeWidth={1.5}
          fill={`url(#spark-${agentId})`}
          isAnimationActive={false}
        />
      </AreaChart>
    </div>
  );
}
