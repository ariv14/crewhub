// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useChannelAnalytics } from "@/lib/hooks/use-channels";
import { formatCredits } from "@/lib/utils";

interface AnalyticsChartsProps {
  channelId: string;
}

export function AnalyticsCharts({ channelId }: AnalyticsChartsProps) {
  const { data, isLoading } = useChannelAnalytics(channelId);

  if (isLoading) {
    return <p className="py-8 text-center text-sm text-muted-foreground">Loading analytics…</p>;
  }

  if (!data || (!data.daily_messages.length && !data.daily_credits.length)) {
    return <p className="py-8 text-center text-sm text-muted-foreground">No analytics data yet</p>;
  }

  const msgData = data.daily_messages.map((d) => ({
    date: d.date.slice(5), // "MM-DD"
    count: d.count,
  }));

  const creditData = data.daily_credits.map((d) => ({
    date: d.date.slice(5),
    amount: d.amount,
  }));

  return (
    <div className="grid gap-6 sm:grid-cols-2">
      <div>
        <p className="mb-3 text-sm font-medium">Message Volume</p>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={msgData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="msgGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "6px",
                  fontSize: 12,
                }}
                labelStyle={{ color: "hsl(var(--foreground))" }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#a855f7"
                strokeWidth={2}
                fill="url(#msgGradient)"
                name="Messages"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div>
        <p className="mb-3 text-sm font-medium">Credit Usage</p>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={creditData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
                tickFormatter={(v) => formatCredits(v)}
              />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "6px",
                  fontSize: 12,
                }}
                labelStyle={{ color: "hsl(var(--foreground))" }}
                formatter={(value: number | undefined) => [formatCredits(value ?? 0), "Credits"]}
              />
              <Bar
                dataKey="amount"
                fill="#6366f1"
                radius={[3, 3, 0, 0]}
                name="Credits"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
