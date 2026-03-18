// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState, useMemo, useEffect } from "react";
import { useParams, usePathname } from "next/navigation";
import {
  ArrowUp,
  ArrowDown,
  CheckCircle2,
  Copy,
  Check,
  GitBranch,
  Globe,
  Loader2,
  Lock,
  Pencil,
  Play,
  RotateCcw,
  Save,
  Trash2,
  XCircle,
  Zap,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { useQueryClient } from "@tanstack/react-query";
import {
  useCrew,
  useUpdateCrew,
  useDeleteCrew,
  useRunCrew,
  useCloneCrew,
} from "@/lib/hooks/use-crews";
import { useConvertCrewToWorkflow } from "@/lib/hooks/use-workflows";
import { useTask } from "@/lib/hooks/use-tasks";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import type { Crew, CrewMember } from "@/types/crew";
import type { Task, Artifact } from "@/types/task";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function extractArtifactText(artifacts: Artifact[]): string {
  const parts: string[] = [];
  for (const a of artifacts) {
    for (const p of a.parts) {
      if (p.type === "text" && p.content) parts.push(p.content);
    }
  }
  return parts.join("\n\n");
}

function TaskPoller({
  taskId,
  onUpdate,
}: {
  taskId: string;
  onUpdate: (task: Task) => void;
}) {
  const { data: task } = useTask(taskId);
  useEffect(() => { if (task) onUpdate(task); }, [task, onUpdate]);
  return null;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant="outline"
      size="sm"
      className="gap-1.5"
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
    >
      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Copied" : "Copy result"}
    </Button>
  );
}

// ---------------------------------------------------------------------------
// Member row (for edit mode with reorder)
// ---------------------------------------------------------------------------
function MemberRow({
  member,
  index,
  total,
  onMoveUp,
  onMoveDown,
  onRemove,
  editing,
}: {
  member: CrewMember;
  index: number;
  total: number;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onRemove: () => void;
  editing: boolean;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card p-3">
      {editing && (
        <div className="flex flex-col gap-0.5">
          <button
            onClick={onMoveUp}
            disabled={index === 0}
            className="rounded p-0.5 hover:bg-muted disabled:opacity-30"
          >
            <ArrowUp className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onMoveDown}
            disabled={index === total - 1}
            className="rounded p-0.5 hover:bg-muted disabled:opacity-30"
          >
            <ArrowDown className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-sm font-bold">
        {member.agent?.name?.charAt(0) || "?"}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{member.agent?.name || "Unknown Agent"}</p>
        <p className="truncate text-xs text-muted-foreground">{member.skill?.name || "Unknown Skill"}</p>
      </div>
      <Badge variant="outline" className="shrink-0 text-[10px]">#{index + 1}</Badge>
      {editing && (
        <button onClick={onRemove} className="rounded p-1 hover:bg-red-500/10">
          <Trash2 className="h-3.5 w-3.5 text-red-400" />
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline run results
// ---------------------------------------------------------------------------
function RunResults({
  crew,
  taskIds,
  memberTaskMap,
}: {
  crew: Crew;
  taskIds: string[];
  memberTaskMap: Record<string, string>;
}) {
  const [taskMap, setTaskMap] = useState<Map<string, Task>>(new Map());

  function handleTaskUpdate(agentId: string, task: Task) {
    setTaskMap((prev) => {
      const existing = prev.get(agentId);
      if (existing?.status === task.status && existing?.artifacts?.length === task.artifacts?.length) return prev;
      const next = new Map(prev);
      next.set(agentId, task);
      return next;
    });
  }

  const completedCount = Array.from(taskMap.values()).filter((t) => t.status === "completed").length;
  const failedCount = Array.from(taskMap.values()).filter((t) => t.status === "failed").length;
  const totalDone = completedCount + failedCount;
  const total = crew.members.length;
  const pct = total > 0 ? Math.round((totalDone / total) * 100) : 0;

  const markdown = useMemo(() => {
    const sections: string[] = [`# Crew Result\n\n---\n`];
    for (const member of crew.members) {
      const task = taskMap.get(member.agent_id);
      if (!task) continue;
      if (task.status === "completed" && task.artifacts?.length) {
        const text = extractArtifactText(task.artifacts);
        sections.push(`## ${member.skill?.name}\n*By ${member.agent?.name}*\n\n${text}\n\n---\n`);
      } else if (task.status === "failed") {
        sections.push(`## ${member.skill?.name}\n*By ${member.agent?.name}*\n\n> This agent failed.\n\n---\n`);
      }
    }
    return sections.join("\n");
  }, [crew.members, taskMap]);

  return (
    <div className="space-y-4">
      {/* Invisible pollers */}
      {crew.members.map((m) => {
        const tid = memberTaskMap[m.agent_id];
        if (!tid) return null;
        return (
          <TaskPoller
            key={tid}
            taskId={tid}
            onUpdate={(task) => handleTaskUpdate(m.agent_id, task)}
          />
        );
      })}

      {/* Progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {totalDone < total ? (
              <span className="flex items-center gap-2">
                <SpinningLogo spinning size="sm" />
                {completedCount} of {total} agents complete
                {failedCount > 0 && <span className="text-red-400">({failedCount} failed)</span>}
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
              totalDone === total ? "bg-green-500" : "bg-primary"
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Agent status pills */}
      <div className="flex flex-wrap gap-2">
        {crew.members.map((m) => {
          const task = taskMap.get(m.agent_id);
          const status = task?.status;
          const isWorking = status && ["submitted", "working", "input_required"].includes(status);
          const isCompleted = status === "completed";
          const isFailed = status === "failed";
          return (
            <div
              key={m.id}
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
              <span className="font-medium">{m.skill?.name}</span>
            </div>
          );
        })}
      </div>

      {/* Report */}
      {totalDone > 0 && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <CopyButton text={markdown} />
          </div>
          <div className="rounded-xl border bg-card p-6">
            <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:mt-6 prose-headings:mb-3 prose-h1:text-xl prose-h2:text-lg prose-h2:border-b prose-h2:pb-2 prose-hr:my-6 prose-pre:bg-muted prose-pre:text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{markdown}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      {totalDone === 0 && (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <SpinningLogo spinning size="lg" />
          <p className="text-sm text-muted-foreground">Your crew is working on this...</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CrewDetailClient({ id: serverId }: { id: string }) {
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  const pathId = pathname.split("/").filter(Boolean).pop();
  const realId =
    (params?.id && params.id !== "__fallback" ? params.id : null) ??
    (serverId && serverId !== "__fallback" ? serverId : null) ??
    (pathId && pathId !== "__fallback" ? pathId : null) ??
    "";

  const queryClient = useQueryClient();
  const { data: crew, isLoading } = useCrew(realId);
  const updateCrew = useUpdateCrew(realId);
  const deleteCrew = useDeleteCrew();
  const runCrew = useRunCrew();
  const cloneCrew = useCloneCrew();
  const convertMutation = useConvertCrewToWorkflow();

  // Edit state
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editIcon, setEditIcon] = useState("");
  const [editPublic, setEditPublic] = useState(false);
  const [editMembers, setEditMembers] = useState<CrewMember[]>([]);

  // Run state
  const [runMessage, setRunMessage] = useState("");
  const [runResult, setRunResult] = useState<{
    taskIds: string[];
    memberTaskMap: Record<string, string>;
  } | null>(null);
  const [running, setRunning] = useState(false);

  // Dialogs
  const [showDelete, setShowDelete] = useState(false);

  function startEditing() {
    if (!crew) return;
    setEditName(crew.name);
    setEditDesc(crew.description || "");
    setEditIcon(crew.icon || "");
    setEditPublic(crew.is_public);
    setEditMembers([...crew.members].sort((a, b) => a.position - b.position));
    setEditing(true);
  }

  function cancelEditing() {
    setEditing(false);
  }

  function moveUp(idx: number) {
    if (idx === 0) return;
    setEditMembers((prev) => {
      const next = [...prev];
      [next[idx - 1], next[idx]] = [next[idx], next[idx - 1]];
      return next;
    });
  }

  function moveDown(idx: number) {
    setEditMembers((prev) => {
      if (idx >= prev.length - 1) return prev;
      const next = [...prev];
      [next[idx], next[idx + 1]] = [next[idx + 1], next[idx]];
      return next;
    });
  }

  function removeMember(idx: number) {
    setEditMembers((prev) => prev.filter((_, i) => i !== idx));
  }

  async function handleSave() {
    await updateCrew.mutateAsync({
      name: editName,
      description: editDesc || undefined,
      icon: editIcon || undefined,
      is_public: editPublic,
      members: editMembers.map((m, i) => ({
        agent_id: m.agent_id,
        skill_id: m.skill_id,
        position: i,
      })),
    });
    await queryClient.refetchQueries({ queryKey: ["crews", realId] });
    setEditing(false);
  }

  async function handleRun() {
    if (!runMessage.trim()) return;
    setRunning(true);
    setRunResult(null);
    try {
      const result = await runCrew.mutateAsync({
        id: realId,
        data: { message: runMessage.trim() },
      });
      setRunResult({
        taskIds: result.task_ids,
        memberTaskMap: result.member_task_map,
      });
    } finally {
      setRunning(false);
    }
  }

  async function handleConvertToWorkflow() {
    try {
      const workflow = await convertMutation.mutateAsync(realId);
      window.location.href = ROUTES.workflowDetail(workflow.id);
    } catch {
      // React Query will surface the error state on the mutation
    }
  }

  async function handleClone() {
    try {
      const newCrew = await cloneCrew.mutateAsync(realId);
      window.location.href = ROUTES.crewDetail(newCrew.id);
    } catch {
      // React Query will surface the error state on the mutation
    }
  }

  async function handleDelete() {
    try {
      await deleteCrew.mutateAsync(realId);
      window.location.href = ROUTES.myCrews;
    } catch {
      setShowDelete(false);
    }
  }

  if (isLoading || !crew) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <SpinningLogo spinning size="lg" />
      </div>
    );
  }

  const sortedMembers = [...crew.members].sort((a, b) => a.position - b.position);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-4">
          {editing ? (
            <Input
              value={editIcon}
              onChange={(e) => setEditIcon(e.target.value)}
              placeholder="👥"
              className="h-12 w-12 text-center text-lg"
              maxLength={4}
            />
          ) : (
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-2xl">
              {crew.icon || "👥"}
            </div>
          )}
          <div>
            {editing ? (
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="text-lg font-bold"
              />
            ) : (
              <h1 className="text-2xl font-bold">{crew.name}</h1>
            )}
            <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="outline" className="text-[10px]">
                {crew.is_public ? (
                  <><Globe className="mr-1 h-3 w-3" />Public</>
                ) : (
                  <><Lock className="mr-1 h-3 w-3" />Private</>
                )}
              </Badge>
              <span>{crew.members.length} member{crew.members.length !== 1 ? "s" : ""}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {editing ? (
            <>
              <Button variant="outline" size="sm" onClick={cancelEditing}>Cancel</Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={updateCrew.isPending || !editName.trim() || editMembers.length === 0}
                className="gap-1"
              >
                {updateCrew.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                Save
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" size="sm" onClick={startEditing} className="gap-1">
                <Pencil className="h-3.5 w-3.5" />
                Edit
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleConvertToWorkflow}
                disabled={convertMutation.isPending}
                className="gap-1"
              >
                {convertMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <GitBranch className="h-3.5 w-3.5" />
                )}
                Convert to Workflow
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleClone}
                disabled={cloneCrew.isPending}
                className="gap-1"
              >
                <Copy className="h-3.5 w-3.5" />
                Clone
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDelete(true)}
                className="gap-1 text-red-400 hover:text-red-400"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Description */}
      {editing ? (
        <div className="space-y-3">
          <Textarea
            value={editDesc}
            onChange={(e) => setEditDesc(e.target.value)}
            placeholder="Description (optional)"
            className="min-h-[80px] resize-none"
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={editPublic}
              onChange={(e) => setEditPublic(e.target.checked)}
              className="rounded"
            />
            Make this crew public (others can clone it)
          </label>
        </div>
      ) : crew.description ? (
        <p className="text-sm text-muted-foreground">{crew.description}</p>
      ) : null}

      {/* Members */}
      <div>
        <h2 className="mb-3 text-lg font-semibold">Members</h2>
        <div className="grid gap-2">
          {(editing ? editMembers : sortedMembers).map((m, i) => (
            <MemberRow
              key={m.id}
              member={m}
              index={i}
              total={(editing ? editMembers : sortedMembers).length}
              onMoveUp={() => moveUp(i)}
              onMoveDown={() => moveDown(i)}
              onRemove={() => removeMember(i)}
              editing={editing}
            />
          ))}
          {editing && editMembers.length === 0 && (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No members left. A crew needs at least one member.
            </p>
          )}
        </div>
      </div>

      {/* Inline Run */}
      {!editing && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Run Crew</h2>
          <div className="rounded-xl border bg-card p-1 shadow-sm transition-all focus-within:border-primary/40">
            <Textarea
              value={runMessage}
              onChange={(e) => setRunMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleRun();
                }
              }}
              placeholder="Enter your goal or message for the crew..."
              className="min-h-[80px] resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
            />
            <div className="flex items-center justify-end px-2 pb-2">
              <Button
                onClick={handleRun}
                disabled={running || !runMessage.trim()}
                className="gap-1"
              >
                {running ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Zap className="h-4 w-4" />
                )}
                Run Crew
              </Button>
            </div>
          </div>

          {/* Results */}
          {runResult && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Results</h3>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1"
                  onClick={() => setRunResult(null)}
                >
                  <RotateCcw className="h-3 w-3" />
                  New Run
                </Button>
              </div>
              <RunResults
                crew={crew}
                taskIds={runResult.taskIds}
                memberTaskMap={runResult.memberTaskMap}
              />
            </div>
          )}
        </div>
      )}

      {/* Delete dialog */}
      <ConfirmDialog
        open={showDelete}
        onOpenChange={setShowDelete}
        title="Delete Crew"
        description={`Delete "${crew.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        loading={deleteCrew.isPending}
        onConfirm={handleDelete}
      />
    </div>
  );
}
