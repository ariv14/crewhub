"use client";

import { useState, useMemo } from "react";
import {
  Users,
  Zap,
  Loader2,
  Star,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  Circle,
  Coins,
  Save,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useCreateTask, useTask } from "@/lib/hooks/use-tasks";
import { useCreateCrew } from "@/lib/hooks/use-crews";
import { suggestAgents } from "@/lib/api/tasks";
import { useAuth } from "@/lib/auth-context";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { SkillSuggestion, Task, Artifact } from "@/types/task";

const TEAM_STARTERS = [
  "I'm launching a SaaS product next month. Help me plan everything.",
  "Review my REST API design for security, performance, and test coverage.",
  "I need to redesign my app's onboarding flow for better conversion.",
  "Help me set up a CI/CD pipeline with proper testing and monitoring.",
];

// ---------------------------------------------------------------------------
// Utility: extract plain text from task artifacts
// ---------------------------------------------------------------------------
function extractArtifactText(artifacts: Artifact[]): string {
  const parts: string[] = [];
  for (const artifact of artifacts) {
    for (const part of artifact.parts) {
      if (part.type === "text" && part.content) {
        parts.push(part.content);
      }
    }
  }
  return parts.join("\n\n");
}

// ---------------------------------------------------------------------------
// Task poller — invisible component that polls a single task and reports back
// ---------------------------------------------------------------------------
function TaskPoller({
  taskId,
  onUpdate,
}: {
  taskId: string;
  onUpdate: (task: Task) => void;
}) {
  const { data: task } = useTask(taskId);
  // Report task data to parent on each render
  if (task) onUpdate(task);
  return null;
}

// ---------------------------------------------------------------------------
// Progress bar for team completion
// ---------------------------------------------------------------------------
function TeamProgressBar({
  completed,
  failed,
  total,
}: {
  completed: number;
  failed: number;
  total: number;
}) {
  const done = completed + failed;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          {done < total ? (
            <span className="flex items-center gap-2">
              <SpinningLogo spinning size="sm" />
              {completed} of {total} agents complete
              {failed > 0 && (
                <span className="text-red-400">({failed} failed)</span>
              )}
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-green-500">
              <CheckCircle2 className="h-4 w-4" />
              All {total} agents complete
            </span>
          )}
        </span>
        <span className="text-xs text-muted-foreground">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            done === total ? "bg-green-500" : "bg-primary"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Copy button
// ---------------------------------------------------------------------------
function CopyAllButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  function handleCopy() {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }
  return (
    <Button variant="outline" size="sm" onClick={handleCopy} className="gap-1.5">
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5" />
          Copied
        </>
      ) : (
        <>
          <Copy className="h-3.5 w-3.5" />
          Copy full result
        </>
      )}
    </Button>
  );
}

// ---------------------------------------------------------------------------
// Consolidated report — single merged document from all agents
// ---------------------------------------------------------------------------
function ConsolidatedReport({
  suggestions,
  taskMap,
  goal,
}: {
  suggestions: SkillSuggestion[];
  taskMap: Map<string, Task>;
  goal: string;
}) {
  // Build a single markdown document with sections per agent
  const { markdown, allDone, completedCount, failedCount } = useMemo(() => {
    let completed = 0;
    let failed = 0;
    const sections: string[] = [];

    sections.push(`# Team Result\n\n**Goal:** ${goal}\n\n---\n`);

    for (const suggestion of suggestions) {
      const task = taskMap.get(suggestion.agent.id);
      if (!task) continue;

      if (task.status === "completed" && task.artifacts?.length > 0) {
        completed++;
        const text = extractArtifactText(task.artifacts);
        sections.push(
          `## ${suggestion.skill.name}\n*By ${suggestion.agent.name}*\n\n${text}\n\n---\n`
        );
      } else if (task.status === "failed") {
        failed++;
        sections.push(
          `## ${suggestion.skill.name}\n*By ${suggestion.agent.name}*\n\n> This agent failed to complete the task.\n\n---\n`
        );
      }
    }

    return {
      markdown: sections.join("\n"),
      allDone: completed + failed === suggestions.length,
      completedCount: completed,
      failedCount: failed,
    };
  }, [suggestions, taskMap, goal]);

  const totalDone = completedCount + failedCount;

  if (totalDone === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <SpinningLogo spinning size="lg" />
        <p className="text-sm text-muted-foreground">
          Your team is working on this...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Copy button */}
      <div className="flex justify-end">
        <CopyAllButton text={markdown} />
      </div>

      {/* Single merged report */}
      <div className="rounded-xl border bg-card p-6" data-testid="consolidated-report">
        <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:mt-6 prose-headings:mb-3 prose-h1:text-xl prose-h2:text-lg prose-h2:border-b prose-h2:pb-2 prose-hr:my-6 prose-pre:bg-muted prose-pre:text-sm prose-code:text-sm">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Agent status pills — compact row showing who's done
// ---------------------------------------------------------------------------
function AgentStatusRow({
  suggestions,
  taskMap,
}: {
  suggestions: SkillSuggestion[];
  taskMap: Map<string, Task>;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {suggestions.map((s) => {
        const task = taskMap.get(s.agent.id);
        const status = task?.status;
        const isWorking =
          status && ["submitted", "working", "input_required"].includes(status);
        const isCompleted = status === "completed";
        const isFailed = status === "failed";

        return (
          <div
            key={s.agent.id}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs",
              isCompleted && "border-green-500/30 bg-green-500/5 text-green-500",
              isFailed && "border-red-500/30 bg-red-500/5 text-red-400",
              isWorking && "border-primary/30 bg-primary/5 text-primary",
              !status && "border-border text-muted-foreground"
            )}
          >
            {isWorking && <SpinningLogo spinning size="sm" />}
            {isCompleted && <CheckCircle2 className="h-3 w-3" />}
            {isFailed && <XCircle className="h-3 w-3" />}
            <span className="font-medium">{s.skill.name}</span>
            <span className="text-muted-foreground">
              ({s.agent.name.replace("AI Agency: ", "")})
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Cost helper — extract credits_per_unit from agent pricing
// ---------------------------------------------------------------------------
function getAgentCost(suggestion: SkillSuggestion): number {
  const pricing = suggestion.agent.pricing;
  if (!pricing) return 0;
  const defaultTier = pricing.tiers?.find((t) => t.is_default);
  return defaultTier?.credits_per_unit ?? pricing.credits ?? 0;
}

// ---------------------------------------------------------------------------
// Suggestion card (selection phase)
// ---------------------------------------------------------------------------
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
  const cost = getAgentCost(suggestion);
  return (
    <button
      onClick={onToggle}
      className={cn(
        "flex items-center gap-3 rounded-xl border p-4 text-left transition-all",
        selected
          ? "border-primary bg-primary/5 shadow-sm"
          : "border-border opacity-60 hover:border-primary/30 hover:opacity-100"
      )}
      data-testid="team-suggestion"
    >
      {/* Selection indicator */}
      <div className="shrink-0">
        {selected ? (
          <CheckCircle2 className="h-5 w-5 text-primary" />
        ) : (
          <Circle className="h-5 w-5 text-muted-foreground" />
        )}
      </div>
      <div
        className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-bold",
          selected
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground"
        )}
      >
        {suggestion.agent.name.charAt(0)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-semibold">
            {suggestion.agent.name}
          </span>
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
            pct >= 60
              ? "text-green-500"
              : pct >= 40
                ? "text-amber-500"
                : "text-red-400"
          )}
        >
          {pct}%
        </span>
        <p className="text-[10px] text-muted-foreground">match</p>
        {cost > 0 && (
          <p className="mt-0.5 text-[10px] text-muted-foreground">
            {cost} credits
          </p>
        )}
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
type Phase = "input" | "selecting" | "working";

export default function TeamPage() {
  const { user } = useAuth();
  const [goal, setGoal] = useState("");
  const [phase, setPhase] = useState<Phase>("input");
  const [suggestions, setSuggestions] = useState<SkillSuggestion[]>([]);
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(
    new Set()
  );
  const [taskIdsByAgent, setTaskIdsByAgent] = useState<Map<string, string>>(
    new Map()
  );
  const [taskMap, setTaskMap] = useState<Map<string, Task>>(new Map());
  const [dispatching, setDispatching] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createTask = useCreateTask();
  const createCrew = useCreateCrew();
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [crewName, setCrewName] = useState("");
  const [crewDesc, setCrewDesc] = useState("");

  function deduplicateSuggestions(raw: SkillSuggestion[]): SkillSuggestion[] {
    const seen = new Set<string>();
    const result: SkillSuggestion[] = [];
    for (const s of raw) {
      if (!seen.has(s.agent.id)) {
        seen.add(s.agent.id);
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
      const result = await suggestAgents({ message: goal.trim(), limit: 8 });
      const unique = deduplicateSuggestions(result.suggestions);
      setSuggestions(unique);
      setSelectedIndices(new Set(unique.slice(0, 4).map((_, i) => i)));
      setPhase("selecting");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to find agents. Please try again."
      );
    } finally {
      setSearching(false);
    }
  }

  function toggleSelection(index: number) {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
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
        parts: [
          { type: "text", content: goal.trim(), data: null, mime_type: null },
        ],
      };

      const results = await Promise.all(
        selected.map((s) =>
          createTask.mutateAsync({
            provider_agent_id: s.agent.id,
            skill_id: s.skill.id,
            messages: [message],
          })
        )
      );

      const idMap = new Map<string, string>();
      selected.forEach((s, i) => idMap.set(s.agent.id, results[i].id));
      setTaskIdsByAgent(idMap);
      setSuggestions(selected);
      setTaskMap(new Map());
      setPhase("working");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to dispatch tasks. Please try again."
      );
    } finally {
      setDispatching(false);
    }
  }

  function handleTaskUpdate(agentId: string, task: Task) {
    setTaskMap((prev) => {
      const existing = prev.get(agentId);
      if (existing && existing.status === task.status && existing.artifacts?.length === task.artifacts?.length) {
        return prev; // No change, avoid re-render
      }
      const next = new Map(prev);
      next.set(agentId, task);
      return next;
    });
  }

  async function handleSaveAsCrew() {
    if (!crewName.trim() || suggestions.length === 0) return;
    try {
      const crew = await createCrew.mutateAsync({
        name: crewName.trim(),
        description: crewDesc.trim() || undefined,
        is_public: false,
        members: suggestions.map((s, i) => ({
          agent_id: s.agent.id,
          skill_id: s.skill.id,
          position: i,
        })),
      });
      setShowSaveDialog(false);
      setCrewName("");
      setCrewDesc("");
      window.location.href = ROUTES.crewDetail(crew.id);
    } catch {
      setError("Failed to save crew. Please try again.");
      setShowSaveDialog(false);
    }
  }

  function handleReset() {
    setGoal("");
    setPhase("input");
    setSuggestions([]);
    setSelectedIndices(new Set());
    setTaskIdsByAgent(new Map());
    setTaskMap(new Map());
    setError(null);
  }

  // Compute progress
  const completedCount = Array.from(taskMap.values()).filter(
    (t) => t.status === "completed"
  ).length;
  const failedCount = Array.from(taskMap.values()).filter(
    (t) => t.status === "failed"
  ).length;
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
          Describe your goal — we&apos;ll dispatch specialists in parallel and
          deliver one combined result.
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

      {/* Phase: Selecting */}
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
              Select your team members. Their outputs will be merged into a
              single combined result.
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

          {/* Cost summary */}
          {(() => {
            const selected = Array.from(selectedIndices).map((i) => suggestions[i]);
            const totalCost = selected.reduce((sum, s) => sum + getAgentCost(s), 0);
            return (
              <div className="flex items-center justify-between rounded-lg border bg-muted/30 px-4 py-3">
                <div className="flex items-center gap-2 text-sm">
                  <Coins className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Estimated cost:</span>
                  <span className="font-semibold">
                    {totalCost > 0 ? `${totalCost} credits` : "Free"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    ({selectedCount} agent{selectedCount !== 1 ? "s" : ""})
                  </span>
                </div>
                <Button
                  onClick={handleLaunchTeam}
                  disabled={selectedCount === 0 || dispatching}
                  className="gap-2"
                >
                  {dispatching ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Zap className="h-4 w-4" />
                  )}
                  Launch Team
                </Button>
              </div>
            );
          })()}
        </div>
      )}

      {/* Phase: Working → Consolidated result */}
      {phase === "working" && (
        <div className="space-y-6" data-testid="team-results">
          {/* Invisible pollers — one per task */}
          {suggestions.map((s) => {
            const tid = taskIdsByAgent.get(s.agent.id);
            if (!tid) return null;
            return (
              <TaskPoller
                key={tid}
                taskId={tid}
                onUpdate={(task) => handleTaskUpdate(s.agent.id, task)}
              />
            );
          })}

          {/* Goal reminder */}
          <div className="rounded-lg border bg-muted/30 p-4">
            <p className="text-sm font-medium">Goal:</p>
            <p className="mt-1 text-sm text-muted-foreground">{goal}</p>
          </div>

          {/* Progress */}
          <TeamProgressBar
            completed={completedCount}
            failed={failedCount}
            total={suggestions.length}
          />

          {/* Agent status pills */}
          <AgentStatusRow suggestions={suggestions} taskMap={taskMap} />

          {/* Actions */}
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Combined Result</h2>
            <div className="flex gap-2">
              {user && completedCount + failedCount === suggestions.length && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowSaveDialog(true)}
                  className="gap-1"
                >
                  <Save className="h-3 w-3" />
                  Save as Crew
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={handleReset}
                className="gap-1"
              >
                <RotateCcw className="h-3 w-3" />
                New Team
              </Button>
            </div>
          </div>

          {/* The single merged report */}
          <ConsolidatedReport
            suggestions={suggestions}
            taskMap={taskMap}
            goal={goal}
          />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-6 rounded-lg border border-red-500/30 bg-red-500/5 p-4 text-center text-sm text-red-500">
          {error}
        </div>
      )}

      {/* Save as Crew dialog */}
      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save as Crew</DialogTitle>
            <DialogDescription>
              Save this team for easy re-use. You can run it again from My Crews.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <Input
              placeholder="Crew name"
              value={crewName}
              onChange={(e) => setCrewName(e.target.value)}
              autoFocus
            />
            <Textarea
              placeholder="Description (optional)"
              value={crewDesc}
              onChange={(e) => setCrewDesc(e.target.value)}
              className="min-h-[60px] resize-none"
            />
            <p className="text-xs text-muted-foreground">
              {suggestions.length} member{suggestions.length !== 1 ? "s" : ""} will be saved
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSaveDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveAsCrew}
              disabled={!crewName.trim() || createCrew.isPending}
              className="gap-1"
            >
              {createCrew.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
              Save Crew
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
