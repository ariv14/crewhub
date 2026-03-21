// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, ArrowRight, Loader2, LogIn, Plus, Search, Sparkles, Star, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { suggestAgents } from "@/lib/api/tasks";
import { listAgents } from "@/lib/api/agents";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { ROUTES } from "@/lib/constants";
import type { SkillSuggestion } from "@/types/task";

const STARTERS = [
  "Summarize a document",
  "Review my code",
  "Translate to Spanish",
];

function ConfidenceDot({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium",
        pct >= 70
          ? "bg-green-500/10 text-green-500"
          : pct >= 40
            ? "bg-amber-500/10 text-amber-500"
            : "bg-red-400/10 text-red-400"
      )}
    >
      {pct}%
    </span>
  );
}

function CompactSuggestion({
  suggestion,
  query,
  isAuthenticated,
}: {
  suggestion: SkillSuggestion;
  query: string;
  isAuthenticated: boolean;
}) {
  const { agent, skill, confidence } = suggestion;
  const truncatedMsg = query.slice(0, 500);
  const agentCredits = agent.pricing?.credits ?? 0;
  const isPremium = agentCredits > 0;
  const taskUrl = isAuthenticated
    ? `/dashboard/tasks/new/?agent=${agent.id}&skill=${skill.id}${truncatedMsg ? `&message=${encodeURIComponent(truncatedMsg)}` : ""}`
    : isPremium
      ? `/login?redirect=${encodeURIComponent(`/agents/${agent.id}/?tab=try${truncatedMsg ? `&message=${encodeURIComponent(truncatedMsg)}` : ""}`)}`
      : `/agents/${agent.id}/?tab=try${truncatedMsg ? `&message=${encodeURIComponent(truncatedMsg)}` : ""}`;

  return (
    <a
      href={taskUrl}
      className="group flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-accent"
      data-testid="suggestion-card"
    >
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
        {agent.name.charAt(0)}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="truncate text-sm font-medium group-hover:text-primary">
            {agent.name}
          </span>
          {agent.reputation_score > 0 && (
            <span className="flex shrink-0 items-center gap-0.5 text-[10px] text-amber-500">
              <Star className="h-2.5 w-2.5 fill-current" />
              {agent.reputation_score.toFixed(1)}
            </span>
          )}
          <ConfidenceDot confidence={confidence} />
        </div>
        <p className="truncate text-xs text-muted-foreground">
          {skill.name}
          {suggestion.low_confidence && (
            <span className="ml-1.5 inline-flex items-center gap-0.5 text-orange-400">
              <AlertTriangle className="inline h-2.5 w-2.5" />
              low match
            </span>
          )}
        </p>
      </div>
      <span className="shrink-0 rounded-md bg-primary px-2 py-1 text-[11px] font-medium text-primary-foreground opacity-0 transition-opacity group-hover:opacity-100">
        {isAuthenticated ? "Use" : isPremium ? "Sign up" : "Try"}
        <ArrowRight className="ml-1 inline h-3 w-3" />
      </span>
    </a>
  );
}

export function MagicBox() {
  const { user } = useAuth();
  const isAuthenticated = !!user;
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<SkillSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createAvailable, setCreateAvailable] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const pendingSearchRef = useRef<string | null>(null);

  // Auto-search when a starter chip sets the query
  useEffect(() => {
    if (pendingSearchRef.current && query === pendingSearchRef.current) {
      pendingSearchRef.current = null;
      handleSearch();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searched && containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setSearched(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [searched]);

  async function handleSearch() {
    if (query.trim().length < 5) return;
    setLoading(true);
    setError(null);
    setCreateAvailable(false);
    try {
      const result = await suggestAgents({
        message: query.trim(),
        limit: 3,
      });
      setSuggestions(result.suggestions);
      setCreateAvailable(result.create_available ?? false);
      setSearched(true);
    } catch (err) {
      // Fall back to public agent list with client-side keyword matching
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        try {
          const agentResult = await listAgents({ per_page: 100, status: "active" });
          const words = query.trim().toLowerCase().split(/\s+/).filter((w) => w.length > 2);

          // Score each agent+skill pair by keyword overlap
          const scored: { agent: typeof agentResult.agents[0]; skill: typeof agentResult.agents[0]["skills"][0]; score: number }[] = [];
          for (const a of agentResult.agents) {
            const agentText = `${a.name} ${a.description} ${a.category} ${a.tags.join(" ")}`.toLowerCase();
            for (const s of a.skills) {
              const skillText = `${s.name} ${s.description}`.toLowerCase();
              const combined = `${agentText} ${skillText}`;
              const hits = words.filter((w) => combined.includes(w)).length;
              if (hits > 0) scored.push({ agent: a, skill: s, score: hits / words.length });
            }
          }

          scored.sort((a, b) => b.score - a.score);
          const top = scored.slice(0, 3);

          const fallback: SkillSuggestion[] = top.map(({ agent: a, skill: s, score }) => ({
            agent: {
              id: a.id,
              name: a.name,
              description: a.description,
              version: a.version,
              category: a.category,
              reputation_score: a.reputation_score,
              avg_latency_ms: a.avg_latency_ms,
              total_tasks: a.total_tasks_completed,
              skills: a.skills.map((sk) => ({
                id: sk.id,
                name: sk.name,
                description: sk.description,
              })),
              pricing: a.pricing ? {
                tiers: a.pricing.tiers,
                credits: a.pricing.credits,
              } : undefined,
            },
            skill: { id: s.id, name: s.name, description: s.description },
            confidence: Math.min(score, 0.8),
            reason: s.description,
            low_confidence: score < 0.4,
          }));
          setSuggestions(fallback);
          setSearched(true);
        } catch {
          setError("Search failed. Try browsing all agents instead.");
        }
      } else {
        setError(err instanceof Error ? err.message : "Search failed");
      }
    } finally {
      setLoading(false);
    }
  }

  const showCreateCta = searched && (createAvailable || suggestions.length === 0 || suggestions.every(s => s.confidence < 0.5)) && !error;

  return (
    <div className="relative mx-auto w-full overflow-hidden" ref={containerRef} data-testid="magic-box">
      {/* Search input */}
      <div className="flex items-center gap-2 rounded-lg border bg-card px-3 py-2 shadow-sm transition-all focus-within:border-primary/40 focus-within:shadow-md focus-within:shadow-primary/5">
        <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleSearch();
            }
          }}
          placeholder="What do you need help with?"
          className="h-7 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/60"
          data-testid="magic-box-input"
        />
        <Button
          onClick={handleSearch}
          disabled={loading || query.trim().length < 5}
          size="sm"
          className="h-7 gap-1 px-3 text-xs"
        >
          {loading ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Zap className="h-3 w-3" />
          )}
          Find
        </Button>
      </div>

      {/* Character hint */}
      {query.length > 0 && query.length < 5 && !searched && (
        <p className="mt-1.5 text-[10px] text-muted-foreground/60">
          Type at least 5 characters to search
        </p>
      )}

      {/* Starters — horizontally scrollable on mobile */}
      {!searched && (
        <div className="mt-2 flex min-w-0 items-center gap-1.5 overflow-x-auto scrollbar-none" data-testid="magic-box-starters">
          <span className="shrink-0 text-[10px] text-muted-foreground/60">Try:</span>
          {STARTERS.map((s) => (
            <button
              key={s}
              onClick={() => {
                setQuery(s);
                pendingSearchRef.current = s;
              }}
              className="shrink-0 whitespace-nowrap rounded-full border border-border/50 px-3 py-2.5 text-xs text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground sm:px-2.5 sm:py-1 sm:text-[11px]"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Results dropdown */}
      {searched && (suggestions.length > 0 || showCreateCta || error) && (
        <div
          className="absolute left-0 right-0 top-full z-50 mt-2 rounded-xl border bg-card shadow-xl"
          data-testid="magic-box-results"
        >
          {suggestions.length > 0 && (
            <div className="divide-y">
              <div className="px-3 py-2">
                <span className="text-[11px] font-medium text-muted-foreground">
                  {suggestions.length} match{suggestions.length !== 1 ? "es" : ""}
                </span>
              </div>
              {suggestions.map((s) => (
                <CompactSuggestion
                  key={`${s.agent.id}-${s.skill.id}`}
                  suggestion={s}
                  query={query}
                  isAuthenticated={isAuthenticated}
                />
              ))}
              <div className="px-3 py-2 text-center">
                <a
                  href={`/agents${query.trim() ? `?q=${encodeURIComponent(query.trim())}` : ""}`}
                  className="text-[11px] text-muted-foreground hover:text-primary"
                >
                  Browse all agents →
                </a>
              </div>
            </div>
          )}

          {/* Compact create CTA */}
          {showCreateCta && (
            <div className="flex items-center gap-3 border-t px-3 py-2.5">
              <Sparkles className="h-4 w-4 shrink-0 text-primary/60" />
              <p className="min-w-0 flex-1 text-xs text-muted-foreground">
                {suggestions.length === 0
                  ? "No match found."
                  : "Want a dedicated specialist?"}
                {" "}
                <a
                  href={
                    isAuthenticated
                      ? `${ROUTES.communityAgents}?create=true&q=${encodeURIComponent(query)}`
                      : `/login?redirect=${encodeURIComponent(`${ROUTES.communityAgents}?create=true&q=${encodeURIComponent(query)}`)}`
                  }
                  className="font-medium text-primary hover:underline"
                >
                  Create one
                </a>
                <span className="ml-1 text-[10px] text-muted-foreground/60">(5 credits)</span>
              </p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="px-3 py-2.5 text-center text-xs text-red-500">
              {error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
