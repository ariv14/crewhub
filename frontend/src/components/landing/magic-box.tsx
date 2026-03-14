"use client";

import { useState } from "react";
import { AlertTriangle, ArrowRight, Loader2, LogIn, Plus, Sparkles, Star, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { suggestAgents } from "@/lib/api/tasks";
import { listAgents } from "@/lib/api/agents";
import { ApiError } from "@/lib/api-client";
import { FeedbackThumbs } from "@/components/shared/feedback-thumbs";
import { useAuth } from "@/lib/auth-context";
import { ROUTES } from "@/lib/constants";
import type { SkillSuggestion } from "@/types/task";

const STARTERS = [
  "Summarize a long document for me",
  "Review my code for bugs",
  "Translate text to Spanish",
  "Write API tests for my endpoint",
  "Help me plan a project",
];

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-muted">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            pct >= 70
              ? "bg-green-500"
              : pct >= 40
                ? "bg-amber-500"
                : "bg-red-400"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] font-medium text-muted-foreground">
        {pct}%
      </span>
    </div>
  );
}

function SuggestionCard({
  suggestion,
  query,
  isAuthenticated,
}: {
  suggestion: SkillSuggestion;
  query: string;
  isAuthenticated: boolean;
}) {
  const { agent, skill, confidence, reason } = suggestion;
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
      className="group block rounded-xl border bg-card p-4 transition-all hover:border-primary/40 hover:shadow-md"
      data-testid="suggestion-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-semibold group-hover:text-primary">
              {agent.name}
            </h3>
            {agent.reputation_score > 0 && (
              <span className="flex items-center gap-0.5 text-[10px] text-amber-500">
                <Star className="h-3 w-3 fill-current" />
                {agent.reputation_score.toFixed(1)}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            using <span className="font-medium text-foreground">{skill.name}</span>
          </p>
        </div>
        <Button size="sm" variant="default" className="shrink-0 gap-1 text-xs">
          {isAuthenticated ? (
            <>
              Use this
              <ArrowRight className="h-3 w-3" />
            </>
          ) : isPremium ? (
            <>
              <LogIn className="h-3 w-3" />
              Sign up
            </>
          ) : (
            <>
              <Sparkles className="h-3 w-3" />
              Try free
            </>
          )}
        </Button>
      </div>

      <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
        {reason}
      </p>

      <div className="mt-2">
        <ConfidenceBar confidence={confidence} />
      </div>

      {suggestion.low_confidence && (
        <div className="mt-2 flex items-center gap-1.5 rounded-md border border-orange-500/30 bg-orange-500/5 px-2 py-1 text-[11px] text-orange-400">
          <AlertTriangle className="h-3 w-3 shrink-0" />
          Low confidence match — results may vary
        </div>
      )}

      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[10px]">
            {agent.category}
          </Badge>
          {agent.total_tasks > 0 && (
            <span className="text-[10px] text-muted-foreground">
              {agent.total_tasks} tasks completed
            </span>
          )}
        </div>
        <FeedbackThumbs
          context="suggestion"
          contextId={`${agent.id}:${skill.id}`}
        />
      </div>
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

  return (
    <div className="mx-auto w-full max-w-2xl" data-testid="magic-box">
      <div className="rounded-xl border bg-card p-1 shadow-lg transition-all focus-within:border-primary/40 focus-within:shadow-primary/5">
        <Textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSearch();
            }
          }}
          placeholder="What do you need help with?"
          className="min-h-[80px] resize-none border-0 bg-transparent text-base shadow-none focus-visible:ring-0"
          data-testid="magic-box-input"
        />
        <div className="flex items-center justify-between px-2 pb-2">
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <Sparkles className="h-3 w-3" />
            {query.trim().length > 0 && query.trim().length < 5
              ? `Type ${5 - query.trim().length} more character${5 - query.trim().length !== 1 ? "s" : ""} to search`
              : "AI-powered agent matching"}
          </div>
          <Button
            onClick={handleSearch}
            disabled={loading || query.trim().length < 5}
            size="sm"
            className="gap-1"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Zap className="h-3.5 w-3.5" />
            )}
            Find Agent
          </Button>
        </div>
      </div>

      {/* Conversation starters */}
      {!searched && (
        <>
          <div className="mt-4 flex flex-wrap justify-center gap-2" data-testid="magic-box-starters">
            {STARTERS.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setQuery(s);
                }}
                className="rounded-full border bg-card px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
              >
                {s}
              </button>
            ))}
          </div>
          <p className="mt-3 text-center text-[11px] text-muted-foreground/70">
            <Sparkles className="mr-1 inline h-3 w-3" />
            Can&apos;t find a match? We&apos;ll <a href={ROUTES.createAgent} className="text-primary hover:underline">create one</a> for you.
          </p>
        </>
      )}

      {/* Results */}
      {searched && suggestions.length > 0 && (
        <div className="mt-6 space-y-3" data-testid="magic-box-results">
          <p className="text-center text-xs text-muted-foreground">
            Found {suggestions.length} agent{suggestions.length !== 1 ? "s" : ""} that can help
          </p>
          {suggestions.map((s) => (
            <SuggestionCard key={`${s.agent.id}-${s.skill.id}`} suggestion={s} query={query} isAuthenticated={isAuthenticated} />
          ))}
          <p className="text-center">
            <a
              href="/agents"
              className="text-xs text-muted-foreground hover:text-primary hover:underline"
            >
              Or browse all agents →
            </a>
          </p>
        </div>
      )}

      {/* Create Agent CTA — shown when no results, low confidence, or API flags it */}
      {searched && (createAvailable || suggestions.length === 0 || suggestions.every(s => s.confidence < 0.5)) && !error && (
        <div
          className="mt-6 rounded-xl border-2 border-dashed border-primary/30 bg-primary/5 p-6 text-center"
          data-testid="magic-box-create-cta"
        >
          <Sparkles className="mx-auto h-8 w-8 text-primary/60" />
          <h3 className="mt-3 font-semibold">
            {suggestions.length === 0
              ? "No specialist found for this yet"
              : "Want a dedicated specialist?"}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            We can create a custom AI agent tailored to your exact need.
          </p>
          <div className="mt-4 flex items-center justify-center gap-3">
            {isAuthenticated ? (
              <a
                href={`${ROUTES.communityAgents}?create=true&q=${encodeURIComponent(query)}`}
              >
                <Button className="gap-1">
                  <Plus className="h-4 w-4" />
                  Create My Agent
                </Button>
              </a>
            ) : (
              <a
                href={`/login?redirect=${encodeURIComponent(`${ROUTES.communityAgents}?create=true&q=${encodeURIComponent(query)}`)}`}
              >
                <Button className="gap-1">
                  <Plus className="h-4 w-4" />
                  Create My Agent
                </Button>
              </a>
            )}
            <a href="/agents">
              <Button variant="outline">Browse all agents</Button>
            </a>
          </div>
          <p className="mt-2 text-[10px] text-muted-foreground">5 credits</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 text-center text-sm text-red-500">
          {error}
        </div>
      )}
    </div>
  );
}
