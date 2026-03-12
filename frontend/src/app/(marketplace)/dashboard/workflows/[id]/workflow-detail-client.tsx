"use client";

import { useState } from "react";
import { useParams, usePathname } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowDown,
  Plus,
  Trash2,
  Save,
  Edit2,
  Play,
  Copy,
  Clock,
  Loader2,
  X,
  GitBranch,
  Users2,
} from "lucide-react";
import {
  useWorkflow,
  useUpdateWorkflow,
  useCloneWorkflow,
  useRunWorkflow,
  useWorkflowRuns,
} from "@/lib/hooks/use-workflows";
import { ROUTES } from "@/lib/constants";
import { formatRelativeTime } from "@/lib/utils";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import type { WorkflowStep, WorkflowRun } from "@/types/workflow";

// --- Step card ---

function StepCard({
  groupNum,
  steps,
  editing,
  onRemoveStep,
}: {
  groupNum: number;
  steps: WorkflowStep[];
  editing: boolean;
  onRemoveStep?: (stepId: string) => void;
}) {
  const isParallel = steps.length > 1;

  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">Step {groupNum + 1}</span>
          {isParallel && (
            <Badge variant="secondary" className="text-[10px]">
              <Users2 className="mr-1 h-3 w-3" />
              Runs in parallel
            </Badge>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {steps.map((step) => (
          <div
            key={step.id}
            className="flex items-center gap-2 rounded-lg border bg-muted/50 px-3 py-2 text-sm"
          >
            <span className="font-medium">
              {step.agent?.name || "Agent"}
            </span>
            <span className="text-muted-foreground">·</span>
            <span className="text-muted-foreground">
              {step.skill?.name || "Skill"}
            </span>
            {step.input_mode !== "chain" && (
              <Badge variant="outline" className="ml-1 text-[10px]">
                {step.input_mode === "original"
                  ? "original input"
                  : "custom"}
              </Badge>
            )}
            {editing && onRemoveStep && (
              <button
                onClick={() => onRemoveStep(step.id)}
                className="ml-1 text-muted-foreground hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Run history card ---

function RunCard({ run }: { run: WorkflowRun }) {
  const statusColors: Record<string, string> = {
    running: "bg-purple-500/15 text-purple-400",
    completed: "bg-green-500/15 text-green-400",
    failed: "bg-red-500/15 text-red-400",
    canceled: "bg-zinc-500/15 text-zinc-400",
  };

  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge className={statusColors[run.status] || ""}>
            {run.status}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {formatRelativeTime(run.created_at)}
          </span>
        </div>
        {run.total_credits_charged != null && (
          <span className="text-xs text-muted-foreground">
            {Number(run.total_credits_charged)} credits
          </span>
        )}
      </div>
      <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">
        {run.input_message}
      </p>
      {run.error && (
        <p className="mt-1 text-xs text-red-400">{run.error}</p>
      )}

      {/* Step run progress */}
      <div className="mt-2 flex gap-1">
        {run.step_runs.map((sr) => {
          const colors: Record<string, string> = {
            pending: "bg-zinc-500/30",
            running: "bg-purple-500",
            completed: "bg-green-500",
            failed: "bg-red-500",
          };
          return (
            <div
              key={sr.id}
              className={`h-1.5 flex-1 rounded-full ${colors[sr.status] || "bg-zinc-500/30"}`}
              title={`Step ${sr.step_group + 1}: ${sr.status}`}
            />
          );
        })}
      </div>
    </div>
  );
}

// --- Main client component ---

export function WorkflowDetailClient({ serverId }: { serverId: string }) {
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  const queryClient = useQueryClient();

  const pathId = pathname.split("/").filter(Boolean).pop();
  const realId =
    (params?.id !== "__fallback" ? params?.id : null) ??
    (serverId !== "__fallback" ? serverId : null) ??
    (pathId !== "__fallback" ? pathId : null) ??
    "";

  const { data: workflow, isLoading } = useWorkflow(realId);
  const { data: runsData } = useWorkflowRuns(realId);
  const updateWorkflow = useUpdateWorkflow(realId);
  const cloneWorkflow = useCloneWorkflow();
  const runWorkflow = useRunWorkflow();

  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [runMessage, setRunMessage] = useState("");
  const [showRunPanel, setShowRunPanel] = useState(false);

  if (isLoading || !workflow) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <SpinningLogo spinning size="lg" />
      </div>
    );
  }

  // Group steps by step_group
  const stepGroups: Record<number, WorkflowStep[]> = {};
  for (const s of workflow.steps) {
    (stepGroups[s.step_group] ??= []).push(s);
  }
  const sortedGroups = Object.keys(stepGroups)
    .map(Number)
    .sort((a, b) => a - b);

  function startEditing() {
    setEditName(workflow!.name);
    setEditDesc(workflow!.description || "");
    setEditing(true);
  }

  async function handleSave() {
    await updateWorkflow.mutateAsync({
      name: editName,
      description: editDesc,
    });
    await queryClient.refetchQueries({ queryKey: ["workflows", realId] });
    setEditing(false);
  }

  async function handleClone() {
    const newWf = await cloneWorkflow.mutateAsync(realId);
    window.location.href = ROUTES.workflowDetail(newWf.id);
  }

  async function handleRun() {
    if (!runMessage.trim()) return;
    await runWorkflow.mutateAsync({ id: realId, data: { message: runMessage } });
    setRunMessage("");
    setShowRunPanel(false);
    queryClient.invalidateQueries({ queryKey: ["workflows", realId, "runs"] });
  }

  const runs = runsData?.runs ?? [];

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild>
            <a href={ROUTES.myWorkflows}>
              <ArrowLeft className="h-4 w-4" />
            </a>
          </Button>
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-lg">
            {workflow.icon}
          </div>
          <div>
            {editing ? (
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="h-8 text-lg font-bold"
              />
            ) : (
              <h1 className="text-2xl font-bold">{workflow.name}</h1>
            )}
            {editing ? (
              <Textarea
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
                className="mt-1"
                rows={2}
                placeholder="Description"
              />
            ) : (
              workflow.description && (
                <p className="mt-1 text-sm text-muted-foreground">
                  {workflow.description}
                </p>
              )
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {editing ? (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setEditing(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={updateWorkflow.isPending}
              >
                {updateWorkflow.isPending ? (
                  <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Save className="mr-1 h-3.5 w-3.5" />
                )}
                Save
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={startEditing}>
                <Edit2 className="mr-1 h-3.5 w-3.5" />
                Edit
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClone}
                disabled={cloneWorkflow.isPending}
              >
                <Copy className="mr-1 h-3.5 w-3.5" />
                Clone
              </Button>
              <Button
                size="sm"
                onClick={() => setShowRunPanel(!showRunPanel)}
              >
                <Play className="mr-1 h-3.5 w-3.5" />
                Run
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Cost limit info */}
      {workflow.max_total_credits && (
        <div className="mt-3 text-sm text-muted-foreground">
          Cost limit: {workflow.max_total_credits} credits per run
        </div>
      )}

      {/* Run panel */}
      {showRunPanel && (
        <div className="mt-4 rounded-xl border bg-card p-4">
          <Label className="text-sm font-medium">Run this workflow</Label>
          <Textarea
            value={runMessage}
            onChange={(e) => setRunMessage(e.target.value)}
            placeholder="Enter your input message..."
            className="mt-2"
            rows={3}
          />
          <div className="mt-3 flex items-center gap-2">
            <Button
              onClick={handleRun}
              disabled={!runMessage.trim() || runWorkflow.isPending}
            >
              {runWorkflow.isPending ? (
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Play className="mr-1 h-3.5 w-3.5" />
              )}
              {runWorkflow.isPending ? "Running..." : "Execute"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowRunPanel(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Pipeline visualization */}
      <div className="mt-6">
        <h2 className="text-lg font-semibold">Pipeline</h2>
        <div className="mt-3 space-y-2">
          {sortedGroups.length === 0 ? (
            <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
              <GitBranch className="mx-auto h-8 w-8 mb-2 opacity-50" />
              No steps yet. Edit this workflow to add agents.
            </div>
          ) : (
            sortedGroups.map((group, i) => (
              <div key={group}>
                <StepCard
                  groupNum={group}
                  steps={stepGroups[group]}
                  editing={editing}
                />
                {i < sortedGroups.length - 1 && (
                  <div className="flex justify-center py-1">
                    <ArrowDown className="h-4 w-4 text-muted-foreground" />
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Schedule button */}
      <div className="mt-4">
        <Button variant="outline" size="sm" asChild>
          <a
            href={`${ROUTES.mySchedules}?type=workflow&target=${realId}&name=${encodeURIComponent(workflow.name)}`}
          >
            <Clock className="mr-1 h-3.5 w-3.5" />
            Schedule This
          </a>
        </Button>
      </div>

      {/* Run history */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold">Run History</h2>
        {runs.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">
            No runs yet. Execute the workflow to see results here.
          </p>
        ) : (
          <div className="mt-3 space-y-2">
            {runs.map((run) => (
              <RunCard key={run.id} run={run} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
