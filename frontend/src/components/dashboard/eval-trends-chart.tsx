"use client";

import { TrendingUp, BarChart3 } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useEvalTrends } from "@/lib/hooks/use-agents";
import type { WeeklyTrend } from "@/lib/api/agents";

/** Format week label "2026-W10" → "W10" for compact axis */
function shortWeek(w: string) {
  return w.replace(/^\d{4}-/, "");
}

function TrendTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { color: string; name: string; value: number | null }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-semibold">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-medium">
            {entry.value != null
              ? entry.name === "Latency"
                ? `${Math.round(entry.value)}ms`
                : entry.name === "Quality"
                  ? `${entry.value}/5`
                  : `${(entry.value * 100).toFixed(0)}%`
              : "--"}
          </span>
        </div>
      ))}
    </div>
  );
}

/** Prepares chart data, scaling quality to 0-1 for dual-axis readability. */
function prepareChartData(trends: WeeklyTrend[]) {
  return trends.map((t) => ({
    week: shortWeek(t.week),
    fullWeek: t.week,
    quality: t.avg_quality,
    success: t.success_rate,
    latency: t.avg_latency_ms,
    tasks: t.task_count,
  }));
}

const COLORS = {
  quality: "#8b5cf6",  // violet
  success: "#10b981",  // emerald
  latency: "#f59e0b",  // amber
};

export function EvalTrendsChart({
  agentId,
  weeks = 8,
}: {
  agentId: string;
  weeks?: number;
}) {
  const { data, isLoading } = useEvalTrends(agentId, weeks);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!data?.trends?.length) {
    return (
      <div
        className="flex h-48 flex-col items-center justify-center rounded-lg border border-dashed"
        data-testid="eval-trends-empty"
      >
        <BarChart3 className="h-8 w-8 text-muted-foreground/50" />
        <p className="mt-2 text-sm text-muted-foreground">
          No evaluation data yet
        </p>
        <p className="text-xs text-muted-foreground/70">
          Trends appear after tasks are completed and scored
        </p>
      </div>
    );
  }

  const chartData = prepareChartData(data.trends);

  // Summary stats from latest week
  const latest = data.trends[data.trends.length - 1];
  const totalTasks = data.trends.reduce((s, t) => s + t.task_count, 0);

  return (
    <div className="space-y-4" data-testid="eval-trends-chart">
      {/* Summary row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MiniStat
          label="Latest Quality"
          value={latest.avg_quality != null ? `${latest.avg_quality}/5` : "--"}
          color={COLORS.quality}
        />
        <MiniStat
          label="Latest Success"
          value={
            latest.success_rate != null
              ? `${(latest.success_rate * 100).toFixed(0)}%`
              : "--"
          }
          color={COLORS.success}
        />
        <MiniStat
          label="Latest Latency"
          value={
            latest.avg_latency_ms != null
              ? `${(latest.avg_latency_ms / 1000).toFixed(1)}s`
              : "--"
          }
          color={COLORS.latency}
        />
        <MiniStat
          label="Total Tasks"
          value={totalTasks}
          color="hsl(var(--primary))"
        />
      </div>

      {/* Chart */}
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
              opacity={0.5}
            />
            <XAxis
              dataKey="week"
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              yAxisId="pct"
              domain={[0, 1]}
              tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <YAxis
              yAxisId="quality"
              orientation="right"
              domain={[0, 5]}
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
              width={30}
            />
            <Tooltip
              content={<TrendTooltip />}
            />
            <Legend
              wrapperStyle={{ fontSize: 12 }}
            />
            <Line
              yAxisId="quality"
              type="monotone"
              dataKey="quality"
              name="Quality"
              stroke={COLORS.quality}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls
            />
            <Line
              yAxisId="pct"
              type="monotone"
              dataKey="success"
              name="Success Rate"
              stroke={COLORS.success}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function MiniStat({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="rounded-lg border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-lg font-bold" style={{ color }}>
        {value}
      </p>
    </div>
  );
}

/** Section wrapper with heading — use in dashboard or agent detail pages. */
export function EvalTrendsSection({
  agentId,
  weeks = 8,
}: {
  agentId: string;
  weeks?: number;
}) {
  return (
    <div className="space-y-3" data-testid="eval-trends-section">
      <div className="flex items-center gap-2">
        <TrendingUp className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold">Quality Trends</h3>
        <span className="text-xs text-muted-foreground">Last {weeks} weeks</span>
      </div>
      <EvalTrendsChart agentId={agentId} weeks={weeks} />
    </div>
  );
}
