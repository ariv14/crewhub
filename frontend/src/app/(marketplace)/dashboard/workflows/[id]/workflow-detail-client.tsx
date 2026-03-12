"use client";

import { useState, useEffect, useRef } from "react";
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
  Search,
} from "lucide-react";
import {
  useWorkflow,
  useUpdateWorkflow,
  useCloneWorkflow,
  useRunWorkflow,
  useWorkflowRuns,
} from "@/lib/hooks/use-workflows";
import { useAgents } from "@/lib/hooks/use-agents";
import { ROUTES } from "@/lib/constants";
import { formatRelativeTime } from "@/lib/utils";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import type { WorkflowStep, WorkflowRun } from "@/types/workflow";
import type { Agent, Skill } from "@/types/agent";

// ---------------------------------------------------------------------------
// Types for edit state (steps before they have server IDs)
// ---------------------------------------------------------------------------
interface EditStep {
  tempId: string;
  agent_id: string;
  skill_id: string;
  step_group: number;
  position: number;
  input_mode: string;
  input_template?: string;
  // Populated for display
  agent_name: string;
  skill_name: string;
}

// ---------------------------------------------------------------------------
// Agent Picker Dialog
// ---------------------------------------------------------------------------
function AgentPicker({
  onSelect,
  onClose,
}: {
  onSelect: (agent: Agent, skill: Skill) => void;
  onClose: () => void;
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  const { data: defaultResults, isLoading: isLoadingDefaults } = useAgents(
    { per_page: 20, status: "active" }
  );
  const { data: searchResults, isFetching: isSearching } = useAgents(
    debouncedQuery
      ? { q: debouncedQuery, per_page: 10, status: "active" }
      : undefined
  );

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!searchQuery.trim()) {
      setDebouncedQuery("");
      return;
    }
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(searchQuery.trim());
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchQuery]);

  const displayAgents = debouncedQuery
    ? searchResults?.agents ?? []
    : defaultResults?.agents ?? [];

  return (
    <div className="rounded-xl border bg-card p-4 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold">
          {selectedAgent ? "Select Skill" : "Add Agent"}
        </h3>
        <button onClick={onClose} className="rounded p-1 hover:bg-muted">
          <X className="h-4 w-4" />
        </button>
      </div>

      {!selectedAgent ? (
        <>
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search agents..."
              className="pl-9"
              autoFocus
            />
          </div>

          {(isSearching || isLoadingDefaults) && (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          )}

          <div className="max-h-60 space-y-1 overflow-y-auto">
            {displayAgents.length === 0 && !isSearching && !isLoadingDefaults ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No agents found
              </p>
            ) : (
              displayAgents.map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => {
                    if (agent.skills?.length === 1) {
                      onSelect(agent, agent.skills[0]);
                    } else {
                      setSelectedAgent(agent);
                    }
                  }}
                  className="flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left text-sm transition-colors hover:bg-accent/50"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-bold">
                    {agent.name?.charAt(0) || "?"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{agent.name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {agent.skills?.length ?? 0} skill{(agent.skills?.length ?? 0) !== 1 ? "s" : ""}
                    </p>
                  </div>
                </button>
              ))
            )}
          </div>
        </>
      ) : (
        <>
          <button
            onClick={() => setSelectedAgent(null)}
            className="mb-3 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" />
            Back to agents
          </button>
          <p className="mb-2 text-sm">
            Select a skill for <strong>{selectedAgent.name}</strong>:
          </p>
          <div className="max-h-48 space-y-1 overflow-y-auto">
            {(selectedAgent.skills ?? []).map((skill) => (
              <button
                key={skill.id}
                onClick={() => onSelect(selectedAgent, skill)}
                className="flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left text-sm transition-colors hover:bg-accent/50"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{skill.name}</p>
                  {skill.description && (
                    <p className="truncate text-xs text-muted-foreground">
                      {skill.description}
                    </p>
                  )}
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step card (edit mode aware)
// ---------------------------------------------------------------------------
function StepCard({
  groupNum,
  steps,
  editing,
  onRemoveStep,
  onAddAgentToStep,
  onChangeInputMode,
}: {
  groupNum: number;
  steps: EditStep[];
  editing: boolean;
  onRemoveStep?: (tempId: string) => void;
  onAddAgentToStep?: (groupNum: number) => void;
  onChangeInputMode?: (tempId: string, mode: string) => void;
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
        {editing && onAddAgentToStep && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 text-xs"
            onClick={() => onAddAgentToStep(groupNum)}
          >
            <Plus className="h-3 w-3" />
            Add Agent
          </Button>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {steps.map((step) => (
          <div
            key={step.tempId}
            className="flex items-center gap-2 rounded-lg border bg-muted/50 px-3 py-2 text-sm"
          >
            <span className="font-medium">{step.agent_name}</span>
            <span className="text-muted-foreground">·</span>
            <span className="text-muted-foreground">{step.skill_name}</span>
            {editing && groupNum > 0 && onChangeInputMode && (
              <select
                value={step.input_mode}
                onChange={(e) => onChangeInputMode(step.tempId, e.target.value)}
                className="ml-1 rounded border bg-background px-1 py-0.5 text-[10px]"
              >
                <option value="chain">chain</option>
                <option value="original">original</option>
                <option value="custom">custom</option>
              </select>
            )}
            {!editing && step.input_mode !== "chain" && (
              <Badge variant="outline" className="ml-1 text-[10px]">
                {step.input_mode === "original" ? "original input" : "custom"}
              </Badge>
            )}
            {editing && onRemoveStep && (
              <button
                onClick={() => onRemoveStep(step.tempId)}
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

// ---------------------------------------------------------------------------
// Run history card
// ---------------------------------------------------------------------------
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
          <Badge className={statusColors[run.status] || ""}>{run.status}</Badge>
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
      {run.error && <p className="mt-1 text-xs text-red-400">{run.error}</p>}
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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
let tempIdCounter = 0;
function newTempId() {
  return `tmp_${++tempIdCounter}_${Date.now()}`;
}

function workflowStepsToEditSteps(steps: WorkflowStep[]): EditStep[] {
  return steps.map((s) => ({
    tempId: s.id,
    agent_id: s.agent_id,
    skill_id: s.skill_id,
    step_group: s.step_group,
    position: s.position,
    input_mode: s.input_mode || "chain",
    input_template: s.input_template || undefined,
    agent_name: s.agent?.name || "Unknown",
    skill_name: s.skill?.name || "Unknown",
  }));
}

function groupEditSteps(steps: EditStep[]) {
  const groups: Record<number, EditStep[]> = {};
  for (const s of steps) {
    (groups[s.step_group] ??= []).push(s);
  }
  return Object.keys(groups)
    .map(Number)
    .sort((a, b) => a - b);
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
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
  const [editSteps, setEditSteps] = useState<EditStep[]>([]);
  const [runMessage, setRunMessage] = useState("");
  const [showRunPanel, setShowRunPanel] = useState(false);

  // Agent picker state
  const [pickerTarget, setPickerTarget] = useState<
    { type: "existing_step"; groupNum: number } | { type: "new_step" } | null
  >(null);

  if (isLoading || !workflow) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <SpinningLogo spinning size="lg" />
      </div>
    );
  }

  // Build display steps (from workflow data or edit state)
  const displaySteps: EditStep[] = editing
    ? editSteps
    : workflowStepsToEditSteps(workflow.steps);
  const sortedGroups = groupEditSteps(displaySteps);

  function startEditing() {
    setEditName(workflow!.name);
    setEditDesc(workflow!.description || "");
    setEditSteps(workflowStepsToEditSteps(workflow!.steps));
    setEditing(true);
  }

  async function handleSave() {
    await updateWorkflow.mutateAsync({
      name: editName,
      description: editDesc,
      steps: editSteps.map((s, i) => ({
        agent_id: s.agent_id,
        skill_id: s.skill_id,
        step_group: s.step_group,
        position: s.position,
        input_mode: s.input_mode,
        input_template: s.input_template,
      })),
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
    await runWorkflow.mutateAsync({
      id: realId,
      data: { message: runMessage },
    });
    setRunMessage("");
    setShowRunPanel(false);
    queryClient.invalidateQueries({
      queryKey: ["workflows", realId, "runs"],
    });
  }

  function handleAddAgent(agent: Agent, skill: Skill) {
    if (!pickerTarget) return;

    const stepGroup =
      pickerTarget.type === "existing_step"
        ? pickerTarget.groupNum
        : sortedGroups.length > 0
          ? sortedGroups[sortedGroups.length - 1] + 1
          : 0;

    const stepsInGroup = editSteps.filter(
      (s) => s.step_group === stepGroup
    );

    const newStep: EditStep = {
      tempId: newTempId(),
      agent_id: agent.id,
      skill_id: skill.id,
      step_group: stepGroup,
      position: stepsInGroup.length,
      input_mode: stepGroup === 0 ? "chain" : "chain",
      agent_name: agent.name,
      skill_name: skill.name,
    };

    setEditSteps((prev) => [...prev, newStep]);
    setPickerTarget(null);
  }

  function handleRemoveStep(tempId: string) {
    setEditSteps((prev) => prev.filter((s) => s.tempId !== tempId));
  }

  function handleChangeInputMode(tempId: string, mode: string) {
    setEditSteps((prev) =>
      prev.map((s) => (s.tempId === tempId ? { ...s, input_mode: mode } : s))
    );
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
                onClick={() => {
                  setEditing(false);
                  setPickerTarget(null);
                }}
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

      {/* Pipeline visualization / builder */}
      <div className="mt-6">
        <h2 className="text-lg font-semibold">Pipeline</h2>
        <div className="mt-3 space-y-2">
          {sortedGroups.length === 0 && !editing ? (
            <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
              <GitBranch className="mx-auto mb-2 h-8 w-8 opacity-50" />
              No steps yet. Click Edit to add agents to this workflow.
            </div>
          ) : sortedGroups.length === 0 && editing ? (
            <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
              <GitBranch className="mx-auto mb-2 h-8 w-8 opacity-50" />
              <p>No steps yet. Add your first agent below.</p>
            </div>
          ) : (
            sortedGroups.map((group, i) => (
              <div key={group}>
                <StepCard
                  groupNum={group}
                  steps={displaySteps.filter((s) => s.step_group === group)}
                  editing={editing}
                  onRemoveStep={editing ? handleRemoveStep : undefined}
                  onAddAgentToStep={
                    editing
                      ? (g) =>
                          setPickerTarget({ type: "existing_step", groupNum: g })
                      : undefined
                  }
                  onChangeInputMode={
                    editing ? handleChangeInputMode : undefined
                  }
                />
                {i < sortedGroups.length - 1 && (
                  <div className="flex justify-center py-1">
                    <ArrowDown className="h-4 w-4 text-muted-foreground" />
                  </div>
                )}
              </div>
            ))
          )}

          {/* Add Step button (editing mode) */}
          {editing && (
            <div className="pt-2">
              {sortedGroups.length > 0 && (
                <div className="flex justify-center pb-2">
                  <ArrowDown className="h-4 w-4 text-muted-foreground" />
                </div>
              )}
              <Button
                variant="outline"
                className="w-full gap-2 border-dashed"
                onClick={() => setPickerTarget({ type: "new_step" })}
              >
                <Plus className="h-4 w-4" />
                Add Step
              </Button>
            </div>
          )}

          {/* Agent Picker (appears when triggered) */}
          {editing && pickerTarget && (
            <div className="mt-3">
              <AgentPicker
                onSelect={handleAddAgent}
                onClose={() => setPickerTarget(null)}
              />
            </div>
          )}
        </div>
      </div>

      {/* Schedule button */}
      {!editing && (
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
      )}

      {/* Run history */}
      {!editing && (
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
      )}
    </div>
  );
}
