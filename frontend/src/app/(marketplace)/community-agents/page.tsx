// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  ArrowRight,
  Flame,
  Loader2,
  Plus,
  Sparkles,
  Star,
  ThumbsUp,
  TrendingUp,
  Zap,
} from "lucide-react";
import { useCustomAgents, useCreateCustomAgent } from "@/lib/hooks/use-custom-agents";
import { useAuth } from "@/lib/auth-context";
import { ROUTES, CATEGORIES } from "@/lib/constants";
import { formatRelativeTime } from "@/lib/utils";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { CustomAgent } from "@/types/custom-agent";

const SORT_OPTIONS = [
  { value: "popular", label: "Most Popular", icon: TrendingUp },
  { value: "tried", label: "Most Tried", icon: Flame },
  { value: "rated", label: "Highest Rated", icon: Star },
  { value: "new", label: "Newest", icon: Sparkles },
];

function AgentCard({ agent }: { agent: CustomAgent }) {
  return (
    <a
      href={ROUTES.communityAgentDetail(agent.id)}
      className="group block rounded-xl border bg-card p-5 transition-all hover:border-primary/30 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold group-hover:text-primary">
            {agent.name}
          </h3>
          <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
            {agent.description}
          </p>
        </div>
        <Button size="sm" variant="ghost" className="shrink-0 gap-1 text-xs">
          Try It <ArrowRight className="h-3 w-3" />
        </Button>
      </div>

      <div className="mt-3 flex items-center gap-3 text-[11px] text-muted-foreground">
        <Badge variant="outline" className="text-[10px]">
          {agent.category}
        </Badge>
        <span className="flex items-center gap-1">
          <Zap className="h-3 w-3" />
          {agent.try_count} tries
        </span>
        <span className="flex items-center gap-1">
          <ThumbsUp className="h-3 w-3" />
          {agent.upvote_count}
        </span>
        {agent.avg_rating > 0 && (
          <span className="flex items-center gap-1">
            <Star className="h-3 w-3 fill-amber-500 text-amber-500" />
            {agent.avg_rating.toFixed(1)}
          </span>
        )}
      </div>

      {agent.status === "promoted" && (
        <div className="mt-2 rounded-md border border-green-500/30 bg-green-500/5 px-2 py-1 text-[10px] text-green-400">
          Production version available
        </div>
      )}
    </a>
  );
}

function CreateAgentDialog() {
  const { user } = useAuth();
  const [message, setMessage] = useState("");
  const [category, setCategory] = useState("");
  const createMutation = useCreateCustomAgent();

  async function handleCreate() {
    if (!message.trim() || message.trim().length < 10) return;
    const result = await createMutation.mutateAsync({
      message: message.trim(),
      category: category || undefined,
      auto_execute: true,
    });
    // Navigate to the created agent
    window.location.href = ROUTES.communityAgentDetail(result.agent.id);
  }

  if (!user) {
    return (
      <div className="rounded-xl border-2 border-dashed border-primary/20 bg-primary/5 p-6 text-center">
        <Sparkles className="mx-auto h-8 w-8 text-primary/60" />
        <h3 className="mt-3 font-semibold">Create Your Own Agent</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Describe what you need and we&apos;ll create a custom AI specialist.
        </p>
        <a href={`/login?redirect=${encodeURIComponent("/community-agents?create=true")}`}>
          <Button className="mt-4 gap-1">
            Sign in to Create <Plus className="h-4 w-4" />
          </Button>
        </a>
      </div>
    );
  }

  return (
    <div className="rounded-xl border-2 border-dashed border-primary/20 bg-primary/5 p-6">
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-primary" />
        <h3 className="font-semibold">Create a Custom Agent</h3>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        Describe the specialist you need. We&apos;ll create it and run your task instantly.
      </p>
      <div className="mt-4 space-y-3">
        <Textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="e.g., Help me write a grant proposal for my university project..."
          className="min-h-[80px] resize-none"
        />
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger className="w-full sm:w-[180px]">
              <SelectValue placeholder="Category (optional)" />
            </SelectTrigger>
            <SelectContent>
              {CATEGORIES.map((c) => (
                <SelectItem key={c.slug} value={c.slug}>
                  {c.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex items-center gap-3">
            <Button
              onClick={handleCreate}
              disabled={createMutation.isPending || message.trim().length < 10}
              className="gap-1"
            >
              {createMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              Create My Agent
            </Button>
            <span className="text-xs text-muted-foreground">5 credits</span>
          </div>
        </div>
        {createMutation.isError && (
          <p className="text-sm text-red-500">
            {(createMutation.error as Error).message || "Failed to create agent"}
          </p>
        )}
      </div>
    </div>
  );
}

function CommunityAgentsContent() {
  const searchParams = useSearchParams();
  const showCreate = searchParams.get("create") === "true";
  const [sort, setSort] = useState(searchParams.get("sort") || "popular");
  const [category, setCategory] = useState(searchParams.get("category") || "");
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useCustomAgents({
    sort,
    category: category || undefined,
    page,
    per_page: 24,
  });

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Community Agents</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Custom AI specialists created by the community
          </p>
        </div>
      </div>

      {/* Create agent section */}
      <div className="mt-6">
        <CreateAgentDialog />
      </div>

      {/* Filters */}
      <div className="mt-8 flex flex-wrap items-center gap-3">
        <div className="flex gap-1 overflow-x-auto rounded-lg border bg-card p-1">
          {SORT_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            return (
              <button
                key={opt.value}
                onClick={() => { setSort(opt.value); setPage(1); }}
                className={`flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  sort === opt.value
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon className="h-3 w-3" />
                {opt.label}
              </button>
            );
          })}
        </div>
        <Select value={category} onValueChange={(v) => { setCategory(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-full sm:w-[160px]">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {CATEGORIES.map((c) => (
              <SelectItem key={c.slug} value={c.slug}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Grid */}
      {isLoading && (
        <div className="mt-12 flex justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {error && (
        <div className="mt-8 text-center text-sm text-red-500">
          Failed to load community agents
        </div>
      )}

      {data && data.agents.length > 0 && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.agents.map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>

          {/* Pagination */}
          {data.total > 24 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {Math.ceil(data.total / 24)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= Math.ceil(data.total / 24)}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}

      {data && data.agents.length === 0 && (
        <EmptyState
          icon={Sparkles}
          title="No community agents yet"
          description="Be the first to create a custom AI specialist!"
        />
      )}
    </div>
  );
}

export default function CommunityAgentsPage() {
  return (
    <Suspense>
      <CommunityAgentsContent />
    </Suspense>
  );
}
