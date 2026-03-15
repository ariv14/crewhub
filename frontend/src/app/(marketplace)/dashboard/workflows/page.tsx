// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import Link from "next/link";
import {
  GitBranch,
  Plus,
  Trash2,
  Globe,
  Lock,
  Play,
  Copy,
} from "lucide-react";
import {
  useMyWorkflows,
  useDeleteWorkflow,
  useCloneWorkflow,
} from "@/lib/hooks/use-workflows";
import { ROUTES } from "@/lib/constants";
import { formatRelativeTime } from "@/lib/utils";
import { EmptyState } from "@/components/shared/empty-state";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";
import type { Workflow } from "@/types/workflow";

function groupSteps(steps: Workflow["steps"]) {
  const groups: Record<number, Workflow["steps"]> = {};
  for (const s of steps) {
    (groups[s.step_group] ??= []).push(s);
  }
  return Object.keys(groups)
    .map(Number)
    .sort((a, b) => a - b);
}

function WorkflowCard({
  workflow,
  onDelete,
}: {
  workflow: Workflow;
  onDelete: (id: string) => void;
}) {
  const stepGroups = groupSteps(workflow.steps);

  return (
    <div className="group relative rounded-xl border bg-card p-5 transition-all hover:border-primary/30 hover:shadow-sm">
      <a
        href={ROUTES.workflowDetail(workflow.id)}
        className="absolute inset-0 z-0"
      />

      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-lg">
            {workflow.icon || "🔗"}
          </div>
          <div>
            <h3 className="font-semibold">{workflow.name}</h3>
            <p className="text-xs text-muted-foreground">
              {stepGroups.length} step{stepGroups.length !== 1 ? "s" : ""} ·{" "}
              {workflow.steps.length} agent
              {workflow.steps.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>

        <div className="relative z-10 flex items-center gap-1">
          <Badge variant="outline" className="text-[10px]">
            {workflow.is_public ? (
              <>
                <Globe className="mr-1 h-3 w-3" />
                Public
              </>
            ) : (
              <>
                <Lock className="mr-1 h-3 w-3" />
                Private
              </>
            )}
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 opacity-0 group-hover:opacity-100"
            onClick={(e) => {
              e.preventDefault();
              onDelete(workflow.id);
            }}
          >
            <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
          </Button>
        </div>
      </div>

      {workflow.description && (
        <p className="mt-3 line-clamp-2 text-sm text-muted-foreground">
          {workflow.description}
        </p>
      )}

      {/* Pipeline visualization */}
      <div className="mt-4 flex items-center gap-1.5 overflow-x-auto">
        {stepGroups.map((group, i) => {
          const stepsInGroup = workflow.steps.filter(
            (s) => s.step_group === group
          );
          return (
            <div key={group} className="flex items-center gap-1.5">
              {i > 0 && (
                <span className="text-xs text-muted-foreground">→</span>
              )}
              <div className="flex items-center gap-0.5">
                {stepsInGroup.map((s) => (
                  <div
                    key={s.id}
                    className="rounded-full border bg-muted/50 px-2 py-0.5 text-[10px]"
                    title={`${s.agent?.name} — ${s.skill?.name}`}
                  >
                    {s.agent?.name?.charAt(0) || "?"}
                  </div>
                ))}
                {stepsInGroup.length > 1 && (
                  <Badge
                    variant="secondary"
                    className="ml-0.5 h-4 px-1 text-[8px]"
                  >
                    parallel
                  </Badge>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
        <span>Updated {formatRelativeTime(workflow.updated_at)}</span>
        <Button
          variant="outline"
          size="sm"
          className="relative z-10 h-7 gap-1 text-xs"
          asChild
        >
          <a href={ROUTES.workflowDetail(workflow.id)}>
            <Play className="h-3 w-3" />
            Run
          </a>
        </Button>
      </div>
    </div>
  );
}

export default function MyWorkflowsPage() {
  const { data, isLoading } = useMyWorkflows();
  const deleteWorkflow = useDeleteWorkflow();
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const workflows = data?.workflows ?? [];

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Workflows</h1>
          <p className="mt-1 text-muted-foreground">
            Multi-step agent pipelines with data chaining
          </p>
        </div>
        <Button asChild>
          <Link href={ROUTES.newWorkflow}>
            <Plus className="mr-2 h-4 w-4" />
            New Workflow
          </Link>
        </Button>
      </div>

      <div className="mt-6">
        {!isLoading && workflows.length === 0 ? (
          <EmptyState
            icon={GitBranch}
            title="No workflows yet"
            description="Create a workflow to chain agents together — output from one step feeds into the next."
            action={
              <Button asChild>
                <Link href={ROUTES.newWorkflow}>Create Workflow</Link>
              </Button>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {workflows.map((wf) => (
              <WorkflowCard
                key={wf.id}
                workflow={wf}
                onDelete={setDeleteTarget}
              />
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete Workflow"
        description="This will permanently delete this workflow and all its run history. This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        loading={deleteWorkflow.isPending}
        onConfirm={() => {
          if (deleteTarget) {
            deleteWorkflow.mutate(deleteTarget, {
              onSuccess: () => setDeleteTarget(null),
              onError: () => setDeleteTarget(null),
            });
          }
        }}
      />
    </div>
  );
}
