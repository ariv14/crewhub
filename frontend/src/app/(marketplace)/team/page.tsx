"use client";

import { useState, useCallback } from "react";
import { Users, Zap, Loader2, ChevronRight, Star, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import { TaskArtifactsDisplay } from "@/components/tasks/task-artifacts-display";
import { useCreateTask, useTask } from "@/lib/hooks/use-tasks";
import { suggestAgents } from "@/lib/api/tasks";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";
import type { SkillSuggestion, Task } from "@/types/task";

const TEAM_STARTERS = [
  "I'm launching a SaaS product next month. Help me plan everything.",
  "Review my REST API design for security, performance, and test coverage.",
  "I need to redesign my app's onboarding flow for better conversion.",
  "Help me set up a CI/CD pipeline with proper testing and monitoring.",
];

// Each dispatched task rendered as its own component (so useTask hook works per-card)
function TeamTaskCard({
  suggestion,
  taskId,
  index,
}: {
  suggestion: SkillSuggestion;
  taskId: string;
  index: number;
}) {
  const { data: task } = useTask(taskId);

  const isWorking =
    task && ["submitted", "working", "input_required"].includes(task.status);
  const isCompleted = task?.status === "completed";
  const isFailed = task?.status === "failed";

  return (
    <div
      className={cn(
        "rounded-xl border bg-card transition-all",
        isCompleted && "border-green-500/30",
        isFailed && "border-red-500/30",
        isWorking && "border-primary/30"
      )}
      style={{ animationDelay: `${index * 150}ms` }}
      data-testid="team-task-card"
    >
      {/* Agent header */}
      <div className="flex items-center gap-3 border-b p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-sm font-bold text-primary">
          {suggestion.agent.name.charAt(0)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-semibold">
              {suggestion.agent.name}
            </h3>
            {suggestion.agent.reputation_score > 0 && (
              <span className="flex items-center gap-0.5 text-[10px] text-amber-500">
                <Star className="h-3 w-3 fill-current" />
                {suggestion.agent.reputation_score.toFixed(1)}
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            {suggestion.skill.name}
          </p>
        </div>
        <div>
          {isWorking && (
            <Badge variant="outline" className="gap-1 border-primary/30 text-primary">
              <SpinningLogo spinning size="sm" />
              Working
            </Badge>
          )}
          {isCompleted && (
            <Badge variant="outline" className="border-green-500/30 text-green-500">
              Done
            </Badge>
          )}
          {isFailed && (
            <Badge variant="outline" className="border-red-500/30 text-red-500">
              Failed
            </Badge>
          )}
        </div>
      </div>

      {/* Results */}
      <div className="p-4">
        {isWorking && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <SpinningLogo spinning size="sm" />
            <span>{suggestion.agent.name} is thinking...</span>
          </div>
        )}

        {isCompleted && task.artifacts && task.artifacts.length > 0 && (
          <div className="max-h-[500px] overflow-y-auto">
            <TaskArtifactsDisplay artifacts={task.artifacts} />
          </div>
        )}

        {isCompleted && (!task.artifacts || task.artifacts.length === 0) && (
          <p className="text-sm text-muted-foreground">
            Completed with no output artifacts.
          </p>
        )}

        {isFailed && (
          <p className="text-sm text-red-500">
            This agent failed to complete the task. The credits have been refunded.
          </p>
        )}
      </div>
    </div>
  );
}

// Suggestion card before dispatch
function TeamSuggestionCard({
  suggestion,
  selected,
  onToggle,
}: {
  suggestion: SkillSuggestion;
  selected: boolean;
  onToggle: () => void;
}) {
  const pct = Math.round(suggestion.confidence * 100);
  return (
    <button
      onClick={onToggle}
      className={cn(
        "flex items-center gap-3 rounded-xl border p-4 text-left transition-all",
        selected
          ? "border-primary bg-primary/5 shadow-sm"
          : "border-border hover:border-primary/30"
      )}
      data-testid="team-suggestion"
    >
      <div
        className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-bold",
          selected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
        )}
      >
        {suggestion.agent.name.charAt(0)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-semibold">{suggestion.agent.name}</span>
          <Badge variant="outline" className="text-[10px]">
            {suggestion.agent.category}
          </Badge>
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {suggestion.skill.name} — {suggestion.reason}
        </p>
      </div>
      <div className="shrink-0 text-right">
        <span
          className={cn(
            "text-xs font-semibold",
            pct >= 60 ? "text-green-500" : pct >= 40 ? "text-amber-500" : "text-red-400"
          )}
        >
          {pct}%
        </span>
        <p className="text-[10px] text-muted-foreground">match</p>
      </div>
    </button>
  );
}

type Phase = "input" | "selecting" | "working" | "done";

export default function TeamPage() {
  const { user } = useAuth();
  const [goal, setGoal] = useState("");
  const [phase, setPhase] = useState<Phase>("input");
  const [suggestions, setSuggestions] = useState<SkillSuggestion[]>([]);
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [taskIds, setTaskIds] = useState<string[]>([]);
  const [dispatching, setDispatching] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createTask = useCreateTask();

  // Deduplicate suggestions: one agent per category/division
  function deduplicateSuggestions(raw: SkillSuggestion[]): SkillSuggestion[] {
    const seen = new Set<string>();
    const result: SkillSuggestion[] = [];
    for (const s of raw) {
      const key = s.agent.id;
      if (!seen.has(key)) {
        seen.add(key);
        result.push(s);
      }
    }
    return result;
  }

  async function handleAssembleTeam() {
    if (goal.trim().length < 10) return;
    setSearching(true);
    setError(null);

    try {
      const result = await suggestAgents({
        message: goal.trim(),
        limit: 8,
      });
      const unique = deduplicateSuggestions(result.suggestions);
      setSuggestions(unique);
      // Pre-select top 4 (or all if fewer)
      const preselect = new Set(unique.slice(0, 4).map((_, i) => i));
      setSelectedIndices(preselect);
      setPhase("selecting");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to find agents. Please try again."
      );
    } finally {
      setSearching(false);
    }
  }

  function toggleSelection(index: number) {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }

  async function handleLaunchTeam() {
    if (selectedIndices.size === 0) return;
    setDispatching(true);
    setError(null);

    try {
      const selected = Array.from(selectedIndices).map((i) => suggestions[i]);
      const message = {
        role: "user",
        parts: [{ type: "text", content: goal.trim(), data: null, mime_type: null }],
      };

      // Dispatch all tasks in parallel
      const results = await Promise.all(
        selected.map((s) =>
          createTask.mutateAsync({
            provider_agent_id: s.agent.id,
            skill_id: s.skill.id,
            messages: [message],
          })
        )
      );

      setTaskIds(results.map((t) => t.id));
      // Reorder suggestions to match dispatched tasks
      setSuggestions(selected);
      setPhase("working");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to dispatch tasks. Please try again."
      );
    } finally {
      setDispatching(false);
    }
  }

  function handleReset() {
    setGoal("");
    setPhase("input");
    setSuggestions([]);
    setSelectedIndices(new Set());
    setTaskIds([]);
    setError(null);
  }

  const selectedCount = selectedIndices.size;

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      {/* Header */}
      <div className="mb-10 text-center">
        <div className="mb-4 flex justify-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
            <Users className="h-7 w-7 text-primary" />
          </div>
        </div>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Assemble Your AI Team
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
          Describe your goal — we'll find the best specialists across all divisions and
          dispatch them in parallel. Get multiple expert perspectives in one shot.
        </p>
      </div>

      {/* Phase: Input */}
      {phase === "input" && (
        <div className="space-y-6" data-testid="team-input">
          <div className="rounded-xl border bg-card p-1 shadow-lg transition-all focus-within:border-primary/40">
            <Textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleAssembleTeam();
                }
              }}
              placeholder="Describe your goal or challenge in detail..."
              className="min-h-[120px] resize-none border-0 bg-transparent text-base shadow-none focus-visible:ring-0"
              data-testid="team-goal-input"
            />
            <div className="flex items-center justify-between px-2 pb-2">
              <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                <Users className="h-3 w-3" />
                Multi-agent team dispatch
              </div>
              <Button
                onClick={handleAssembleTeam}
                disabled={searching || goal.trim().length < 10}
                className="gap-1"
              >
                {searching ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Zap className="h-4 w-4" />
                )}
                Assemble Team
              </Button>
            </div>
          </div>

          {/* Starter prompts */}
          <div className="space-y-2" data-testid="team-starters">
            <p className="text-center text-xs text-muted-foreground">
              Try one of these:
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {TEAM_STARTERS.map((s) => (
                <button
                  key={s}
                  onClick={() => setGoal(s)}
                  className="rounded-lg border bg-card p-3 text-left text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {!user && (
            <p className="text-center text-sm text-muted-foreground">
              <a href="/login" className="text-primary hover:underline">
                Sign in
              </a>{" "}
              to dispatch tasks to your AI team.
            </p>
          )}
        </div>
      )}

      {/* Phase: Selecting team members */}
      {phase === "selecting" && (
        <div className="space-y-6" data-testid="team-selection">
          <div className="rounded-lg border bg-muted/30 p-4">
            <p className="text-sm font-medium">Your goal:</p>
            <p className="mt-1 text-sm text-muted-foreground">{goal}</p>
          </div>

          <div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold">
                Your Team ({selectedCount} selected)
              </h2>
              <Button variant="ghost" size="sm" onClick={handleReset}>
                <RotateCcw className="mr-1 h-3 w-3" />
                Start over
              </Button>
            </div>
            <p className="mb-4 text-sm text-muted-foreground">
              Click to select/deselect agents. Each will work on your goal independently using
              their specialty.
            </p>
            <div className="grid gap-3">
              {suggestions.map((s, i) => (
                <TeamSuggestionCard
                  key={`${s.agent.id}-${s.skill.id}`}
                  suggestion={s}
                  selected={selectedIndices.has(i)}
                  onToggle={() => toggleSelection(i)}
                />
              ))}
            </div>
          </div>

          <div className="flex justify-center">
            <Button
              onClick={handleLaunchTeam}
              disabled={selectedCount === 0 || dispatching}
              size="lg"
              className="gap-2"
            >
              {dispatching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Zap className="h-4 w-4" />
              )}
              Launch {selectedCount} Agent{selectedCount !== 1 ? "s" : ""} in Parallel
            </Button>
          </div>
        </div>
      )}

      {/* Phase: Working / Done */}
      {(phase === "working" || phase === "done") && (
        <div className="space-y-6" data-testid="team-results">
          <div className="rounded-lg border bg-muted/30 p-4">
            <p className="text-sm font-medium">Goal:</p>
            <p className="mt-1 text-sm text-muted-foreground">{goal}</p>
          </div>

          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              Team Results ({taskIds.length} agents)
            </h2>
            <Button variant="outline" size="sm" onClick={handleReset} className="gap-1">
              <RotateCcw className="h-3 w-3" />
              New Team
            </Button>
          </div>

          <div className="grid gap-4">
            {taskIds.map((id, i) => (
              <TeamTaskCard
                key={id}
                suggestion={suggestions[i]}
                taskId={id}
                index={i}
              />
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-6 rounded-lg border border-red-500/30 bg-red-500/5 p-4 text-center text-sm text-red-500">
          {error}
        </div>
      )}
    </div>
  );
}
