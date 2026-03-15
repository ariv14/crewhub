// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import Link from "next/link";
import { BarChart3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ROUTES } from "@/lib/constants";
import { formatCredits } from "@/lib/utils";
import type { SpendByAgentItem } from "@/types/credits";

interface SpendBreakdownProps {
  breakdown: SpendByAgentItem[];
  period: string;
}

export function SpendBreakdown({ breakdown, period }: SpendBreakdownProps) {
  if (breakdown.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-2 py-8 text-center text-muted-foreground">
          <BarChart3 className="h-8 w-8" />
          <p className="text-sm">No spending data for this period</p>
        </CardContent>
      </Card>
    );
  }

  const maxSpent = Math.max(...breakdown.map((b) => b.total_spent));
  const totalSpent = breakdown.reduce((sum, b) => sum + b.total_spent, 0);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            Spend by Agent ({period === "7d" ? "7 days" : period === "30d" ? "30 days" : "90 days"})
          </CardTitle>
          <span className="text-sm text-muted-foreground">
            Total: {formatCredits(totalSpent)} credits (${(totalSpent * 0.01).toFixed(2)})
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {breakdown.map((item) => {
          const pct = maxSpent > 0 ? (item.total_spent / maxSpent) * 100 : 0;
          return (
            <div key={item.agent_id} className="space-y-1.5">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <Link
                    href={ROUTES.agentDetail(item.agent_id)}
                    className="font-medium hover:text-primary hover:underline"
                  >
                    {item.agent_name}
                  </Link>
                  <Badge variant="secondary" className="text-[10px]">
                    {item.agent_category}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 text-muted-foreground">
                  <span>{item.tasks_count} tasks</span>
                  <span className="font-medium text-foreground">
                    {formatCredits(item.total_spent)} credits
                  </span>
                </div>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div
                  className="h-2 rounded-full bg-primary transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <div className="flex justify-between text-[11px] text-muted-foreground">
                <span>Avg: {formatCredits(item.avg_cost)} credits/task</span>
                <span>${(item.total_spent * 0.01).toFixed(2)}</span>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
