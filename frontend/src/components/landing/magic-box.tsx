"use client";

import { useState } from "react";
import { ArrowRight, Loader2, Sparkles, Star, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { suggestAgents } from "@/lib/api/tasks";
import { listAgents } from "@/lib/api/agents";
import { ApiError } from "@/lib/api-client";
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
}: {
  suggestion: SkillSuggestion;
}) {
  const { agent, skill, confidence, reason } = suggestion;

  return (
    <a
      href={`/dashboard/tasks/new/?agent=${agent.id}&skill=${skill.id}`}
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
          Use this
          <ArrowRight className="h-3 w-3" />
        </Button>
      </div>

      <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
        {reason}
      </p>

      <div className="mt-2">
        <ConfidenceBar confidence={confidence} />
      </div>

      <div className="mt-2 flex items-center gap-2">
        <Badge variant="outline" className="text-[10px]">
          {agent.category}
        </Badge>
        {agent.total_tasks > 0 && (
          <span className="text-[10px] text-muted-foreground">
            {agent.total_tasks} tasks completed
          </span>
        )}
      </div>
    </a>
  );
}

export function MagicBox() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<SkillSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch() {
    if (query.trim().length < 5) return;
    setLoading(true);
    setError(null);
    try {
      const result = await suggestAgents({
        message: query.trim(),
        limit: 3,
      });
      setSuggestions(result.suggestions);
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
            AI-powered agent matching
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
      )}

      {/* Results */}
      {searched && suggestions.length > 0 && (
        <div className="mt-6 space-y-3" data-testid="magic-box-results">
          <p className="text-center text-xs text-muted-foreground">
            Found {suggestions.length} agent{suggestions.length !== 1 ? "s" : ""} that can help
          </p>
          {suggestions.map((s) => (
            <SuggestionCard key={`${s.agent.id}-${s.skill.id}`} suggestion={s} />
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

      {/* No results */}
      {searched && suggestions.length === 0 && !error && (
        <div className="mt-6 text-center" data-testid="magic-box-empty">
          <p className="text-sm text-muted-foreground">
            No matching agents found. Try a different description or{" "}
            <a href="/agents" className="text-primary hover:underline">
              browse all agents
            </a>
            .
          </p>
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
