// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import {
  TrendingUp,
  BarChart3,
  Bot,
  User,
  Shield,
  Star,
  Key,
} from "lucide-react";
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
import { cn } from "@/lib/utils";
import type { WeeklyTrend } from "@/lib/api/agents";

type EvalTab = "ai" | "user";

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
              ? entry.name.includes("Latency")
                ? `${Math.round(entry.value)}ms`
                : entry.name.includes("Rate")
                  ? `${(entry.value * 100).toFixed(0)}%`
                  : `${entry.value}/5`
              : "--"}
          </span>
        </div>
      ))}
    </div>
  );
}

const COLORS = {
  quality: "#8b5cf6", // violet
  relevance: "#6366f1", // indigo
  completeness: "#06b6d4", // cyan
  coherence: "#a855f7", // purple
  success: "#10b981", // emerald
  rating: "#f59e0b", // amber
};

function formatModelName(model: string | null): string {
  if (!model) return "Unknown";
  // "groq/llama-3.3-70b-versatile" → "Llama 3.3 70B"
  const name = model.split("/").pop() || model;
  return name
    .replace(/-versatile$/, "")
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatProvider(model: string | null): string {
  if (!model) return "";
  const prefix = model.split("/")[0];
  return prefix.charAt(0).toUpperCase() + prefix.slice(1);
}

// ---------- AI Eval Tab ----------

function AIEvalView({ trends, evalModel }: { trends: WeeklyTrend[]; evalModel: string | null }) {
  const latest = trends[trends.length - 1];
  const totalTasks = trends.reduce((s, t) => s + t.task_count, 0);

  const chartData = trends.map((t) => ({
    week: shortWeek(t.week),
    relevance: t.avg_relevance,
    completeness: t.avg_completeness,
    coherence: t.avg_coherence,
    quality: t.avg_quality,
    success: t.success_rate,
  }));

  return (
    <div className="space-y-4" data-testid="eval-ai-view">
      {/* Model badge */}
      <div className="flex items-center gap-2 text-xs">
        <Bot className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-muted-foreground">Judge:</span>
        <span className="rounded-full bg-violet-500/10 px-2 py-0.5 font-medium text-violet-400">
          {formatModelName(evalModel)}
        </span>
        {evalModel && (
          <span className="text-muted-foreground/60">
            via {formatProvider(evalModel)}
          </span>
        )}
      </div>

      {/* Subscore cards */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <ScoreCard
          label="Relevance"
          value={latest.avg_relevance}
          color={COLORS.relevance}
          description="Does it address what was asked?"
        />
        <ScoreCard
          label="Completeness"
          value={latest.avg_completeness}
          color={COLORS.completeness}
          description="Full scope covered?"
        />
        <ScoreCard
          label="Coherence"
          value={latest.avg_coherence}
          color={COLORS.coherence}
          description="Clear and consistent?"
        />
        <ScoreCard
          label="Overall"
          value={latest.avg_quality}
          color={COLORS.quality}
          description="Average of all dimensions"
          highlight
        />
        <ScoreCard
          label="Success Rate"
          value={latest.success_rate != null ? latest.success_rate * 100 : null}
          color={COLORS.success}
          description={`${totalTasks} tasks scored`}
          suffix="%"
          max={100}
        />
      </div>

      {/* Chart — subscores over time */}
      <div className="h-56 w-full">
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
              domain={[0, 5]}
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
              width={30}
            />
            <Tooltip content={<TrendTooltip />} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              type="monotone"
              dataKey="relevance"
              name="Relevance"
              stroke={COLORS.relevance}
              strokeWidth={1.5}
              dot={{ r: 2 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="completeness"
              name="Completeness"
              stroke={COLORS.completeness}
              strokeWidth={1.5}
              dot={{ r: 2 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="coherence"
              name="Coherence"
              stroke={COLORS.coherence}
              strokeWidth={1.5}
              dot={{ r: 2 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="quality"
              name="Overall"
              stroke={COLORS.quality}
              strokeWidth={2.5}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* BYOK section */}
      <div className="rounded-lg border border-dashed border-muted-foreground/20 p-3">
        <div className="flex items-center gap-2 text-xs">
          <Key className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="font-medium">Bring Your Own Key</span>
          <span className="rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[10px] text-emerald-400">
            Coming soon
          </span>
        </div>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Benchmark with GPT-4o, Claude, or Gemini using your own API key.
          Runs entirely in your browser — we never see your key.
        </p>
        <div className="mt-1.5 flex items-center gap-1.5">
          <Shield className="h-3 w-3 text-emerald-400" />
          <span className="text-[10px] text-emerald-400/80">
            Key never leaves your browser — verifiable in DevTools
          </span>
        </div>
      </div>
    </div>
  );
}

// ---------- User Rating Tab ----------

function UserRatingView({ trends }: { trends: WeeklyTrend[] }) {
  const hasRatings = trends.some((t) => t.avg_rating != null);
  const totalRatings = trends.reduce((s, t) => s + t.rating_count, 0);

  if (!hasRatings) {
    return (
      <div
        className="flex h-48 flex-col items-center justify-center rounded-lg border border-dashed"
        data-testid="eval-user-empty"
      >
        <Star className="h-8 w-8 text-muted-foreground/50" />
        <p className="mt-2 text-sm text-muted-foreground">
          No user ratings yet
        </p>
        <p className="text-xs text-muted-foreground/70">
          Ratings appear when task creators rate completed tasks
        </p>
      </div>
    );
  }

  const latest = trends[trends.length - 1];
  const allRatings = trends.filter((t) => t.avg_rating != null);
  const overallAvg =
    allRatings.reduce((s, t) => s + (t.avg_rating || 0), 0) / allRatings.length;

  const chartData = trends.map((t) => ({
    week: shortWeek(t.week),
    rating: t.avg_rating,
    count: t.rating_count,
  }));

  return (
    <div className="space-y-4" data-testid="eval-user-view">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-2">
        <ScoreCard
          label="Latest Rating"
          value={latest.avg_rating}
          color={COLORS.rating}
          description="Most recent week"
        />
        <ScoreCard
          label="Overall Average"
          value={Math.round(overallAvg * 100) / 100}
          color={COLORS.rating}
          description="Across all weeks"
        />
        <div className="rounded-lg border p-3">
          <p className="text-xs text-muted-foreground">Total Ratings</p>
          <p className="mt-0.5 text-lg font-bold" style={{ color: COLORS.rating }}>
            {totalRatings}
          </p>
          <p className="text-[10px] text-muted-foreground/70">from task creators</p>
        </div>
      </div>

      {/* Rating stars visualization */}
      <div className="flex items-center gap-2">
        <div className="flex">
          {[1, 2, 3, 4, 5].map((star) => (
            <Star
              key={star}
              className={cn(
                "h-4 w-4",
                star <= Math.round(overallAvg)
                  ? "fill-amber-400 text-amber-400"
                  : "text-muted-foreground/30"
              )}
            />
          ))}
        </div>
        <span className="text-sm font-medium">{overallAvg.toFixed(1)}</span>
        <span className="text-xs text-muted-foreground">
          ({totalRatings} rating{totalRatings !== 1 ? "s" : ""})
        </span>
      </div>

      {/* Chart — user ratings over time */}
      <div className="h-48 w-full">
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
              domain={[0, 5]}
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
              width={30}
            />
            <Tooltip content={<TrendTooltip />} />
            <Line
              type="monotone"
              dataKey="rating"
              name="User Rating"
              stroke={COLORS.rating}
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

// ---------- Shared Components ----------

function ScoreCard({
  label,
  value,
  color,
  description,
  highlight,
  suffix = "/5",
  max = 5,
}: {
  label: string;
  value: number | null;
  color: string;
  description?: string;
  highlight?: boolean;
  suffix?: string;
  max?: number;
}) {
  const displayValue = value != null ? value.toFixed(1) : "--";
  const pct = value != null ? (value / max) * 100 : 0;

  return (
    <div
      className={cn(
        "rounded-lg border p-2.5",
        highlight && "border-violet-500/30 bg-violet-500/5"
      )}
    >
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <div className="mt-0.5 flex items-baseline gap-0.5">
        <span className="text-lg font-bold" style={{ color }}>
          {displayValue}
        </span>
        {value != null && (
          <span className="text-[10px] text-muted-foreground">{suffix}</span>
        )}
      </div>
      {/* Mini progress bar */}
      {value != null && (
        <div className="mt-1 h-1 w-full rounded-full bg-muted">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${pct}%`, backgroundColor: color }}
          />
        </div>
      )}
      {description && (
        <p className="mt-0.5 text-[9px] text-muted-foreground/60">
          {description}
        </p>
      )}
    </div>
  );
}

function AgreementBadge({ trends }: { trends: WeeklyTrend[] }) {
  // Calculate agreement between AI quality and user rating
  const paired = trends.filter(
    (t) => t.avg_quality != null && t.avg_rating != null
  );
  if (paired.length === 0) return null;

  const avgDiff =
    paired.reduce(
      (s, t) => s + Math.abs((t.avg_quality || 0) - (t.avg_rating || 0)),
      0
    ) / paired.length;

  // Convert difference to agreement percentage (max diff is 5)
  const agreement = Math.round(((5 - avgDiff) / 5) * 100);
  const isGood = agreement >= 80;

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs",
        isGood
          ? "border-emerald-500/20 bg-emerald-500/5"
          : "border-amber-500/20 bg-amber-500/5"
      )}
      data-testid="eval-agreement"
    >
      <span className="text-muted-foreground">AI ↔ User Agreement:</span>
      <span
        className={cn(
          "font-bold",
          isGood ? "text-emerald-400" : "text-amber-400"
        )}
      >
        {agreement}%
      </span>
      <span className="text-muted-foreground/60">
        {isGood
          ? "AI and users mostly agree"
          : "Notable gap between AI and user scores"}
      </span>
    </div>
  );
}

// ---------- Main Component ----------

export function EvalTrendsChart({
  agentId,
  weeks = 8,
}: {
  agentId: string;
  weeks?: number;
}) {
  const [activeTab, setActiveTab] = useState<EvalTab>("ai");
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

  return (
    <div className="space-y-4" data-testid="eval-trends-chart">
      {/* Tab switcher */}
      <div className="flex gap-1 rounded-lg bg-muted/50 p-1" data-testid="eval-tabs">
        <button
          onClick={() => setActiveTab("ai")}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
            activeTab === "ai"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
          data-testid="eval-tab-ai"
        >
          <Bot className="h-3.5 w-3.5" />
          AI Eval
        </button>
        <button
          onClick={() => setActiveTab("user")}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
            activeTab === "user"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
          data-testid="eval-tab-user"
        >
          <User className="h-3.5 w-3.5" />
          User Ratings
        </button>
      </div>

      {/* Tab content */}
      {activeTab === "ai" ? (
        <AIEvalView trends={data.trends} evalModel={data.eval_model} />
      ) : (
        <UserRatingView trends={data.trends} />
      )}

      {/* Agreement metric — always visible */}
      <AgreementBadge trends={data.trends} />
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
