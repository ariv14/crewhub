// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import {
  Sparkles,
  ArrowRight,
  RotateCcw,
  Pencil,
  Save,
  Loader2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import type { SupervisorPlan, SupervisorPlanStep } from "@/types/workflow";
import {
  useApprovePlan,
  useSupervisorReplan,
} from "@/lib/hooks/use-supervisor";
import { useRunWorkflow } from "@/lib/hooks/use-workflows";

interface SupervisorPlanViewProps {
  plan: SupervisorPlan;
  goal: string;
  onEdit: (workflowId: string) => void;
  onReplan: (newPlan: SupervisorPlan) => void;
  onSaved: (workflowId: string) => void;
}

function StepCard({ step, index }: { step: SupervisorPlanStep; index: number }) {
  return (
    <Card className="border-border/50">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
              {index + 1}
            </div>
            <span className="font-medium">{step.agent_name}</span>
          </div>
          <Badge variant="outline" className="text-xs">
            ~{step.estimated_credits} credits
          </Badge>
        </div>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Skill:</span>
          <span className="text-sm">{step.skill_name}</span>
        </div>
        <div className="mt-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
            <span>Confidence</span>
            <span>{Math.round(step.confidence * 100)}%</span>
          </div>
          <Progress value={step.confidence * 100} className="h-1.5" />
        </div>
        {step.instructions && (
          <p className="mt-2 text-xs text-muted-foreground italic">
            &ldquo;{step.instructions}&rdquo;
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export function SupervisorPlanView({
  plan,
  goal,
  onEdit,
  onReplan,
  onSaved,
}: SupervisorPlanViewProps) {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState("");
  const approveMutation = useApprovePlan();
  const replanMutation = useSupervisorReplan();
  const runMutation = useRunWorkflow();

  const handleApproveAndRun = async () => {
    const workflow = await approveMutation.mutateAsync({
      planId: plan.plan_id,
    });
    await runMutation.mutateAsync({ workflowId: workflow.id, message: goal });
    onSaved(workflow.id);
  };

  const handleSave = async () => {
    const workflow = await approveMutation.mutateAsync({
      planId: plan.plan_id,
    });
    onSaved(workflow.id);
  };

  const handleEdit = async () => {
    const workflow = await approveMutation.mutateAsync({
      planId: plan.plan_id,
    });
    onEdit(workflow.id);
  };

  const handleRegenerate = async () => {
    if (!feedback.trim()) return;
    const newPlan = await replanMutation.mutateAsync({
      goal,
      feedback,
      previousPlanId: plan.plan_id,
    });
    setShowFeedback(false);
    setFeedback("");
    onReplan(newPlan);
  };

  const isLoading =
    approveMutation.isPending ||
    runMutation.isPending ||
    replanMutation.isPending;

  // Group steps by step_group for visual pipeline
  const groups = new Map<number, SupervisorPlanStep[]>();
  plan.steps.forEach((step) => {
    const group = groups.get(step.step_group) || [];
    group.push(step);
    groups.set(step.step_group, group);
  });

  let stepIndex = 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Sparkles className="h-6 w-6 text-primary" />
          <div>
            <h2 className="text-xl font-bold">{plan.name}</h2>
            <p className="text-sm text-muted-foreground">{plan.description}</p>
          </div>
        </div>
        <Badge
          variant="secondary"
          className="border-amber-500/50 text-amber-500"
        >
          Draft
        </Badge>
      </div>

      {/* Goal */}
      <Card className="bg-muted/30">
        <CardContent className="p-4">
          <p className="text-xs font-medium text-muted-foreground mb-1">Goal</p>
          <p className="text-sm">{goal}</p>
        </CardContent>
      </Card>

      {/* Cost estimate */}
      <div className="flex items-center justify-between rounded-lg border p-3">
        <span className="text-sm font-medium">Estimated cost</span>
        <Badge>{plan.total_estimated_credits} credits</Badge>
      </div>

      {/* Pipeline visualization */}
      <div className="space-y-3">
        {Array.from(groups.entries())
          .sort(([a], [b]) => a - b)
          .map(([groupNum, groupSteps], gi) => (
            <div key={groupNum}>
              {gi > 0 && (
                <div className="flex justify-center py-1">
                  <div className="h-6 w-px bg-border" />
                </div>
              )}
              {groupSteps.length > 1 && (
                <Badge variant="outline" className="mb-2 text-xs">
                  Parallel — Group {groupNum}
                </Badge>
              )}
              <div
                className={
                  groupSteps.length > 1 ? "grid gap-2 sm:grid-cols-2" : ""
                }
              >
                {groupSteps.map((step) => {
                  const idx = stepIndex++;
                  return <StepCard key={idx} step={step} index={idx} />;
                })}
              </div>
            </div>
          ))}
      </div>

      {/* Feedback for regeneration */}
      {showFeedback && (
        <Card>
          <CardContent className="p-4 space-y-3">
            <p className="text-sm font-medium">What should be different?</p>
            <Textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="e.g., Use a different translator, add a proofreading step..."
              rows={3}
            />
            <div className="flex gap-2">
              <Button
                onClick={handleRegenerate}
                disabled={!feedback.trim() || isLoading}
              >
                {replanMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RotateCcw className="mr-2 h-4 w-4" />
                )}
                Regenerate
              </Button>
              <Button variant="ghost" onClick={() => setShowFeedback(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Action buttons */}
      <div className="flex flex-wrap gap-3">
        <Button onClick={handleApproveAndRun} disabled={isLoading}>
          {approveMutation.isPending || runMutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <ArrowRight className="mr-2 h-4 w-4" />
          )}
          Approve & Run
        </Button>
        <Button variant="outline" onClick={handleEdit} disabled={isLoading}>
          <Pencil className="mr-2 h-4 w-4" /> Edit Plan
        </Button>
        <Button
          variant="outline"
          onClick={() => setShowFeedback(!showFeedback)}
          disabled={isLoading}
        >
          <RotateCcw className="mr-2 h-4 w-4" /> Regenerate
        </Button>
      </div>

      <div className="flex gap-3 border-t pt-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleSave}
          disabled={isLoading}
        >
          <Save className="mr-2 h-4 w-4" /> Save as Workflow
        </Button>
      </div>

      {/* Error display */}
      {(approveMutation.error ||
        replanMutation.error ||
        runMutation.error) && (
        <p className="text-sm text-destructive">
          {(approveMutation.error || replanMutation.error || runMutation.error)
            ?.message || "An error occurred"}
        </p>
      )}
    </div>
  );
}
