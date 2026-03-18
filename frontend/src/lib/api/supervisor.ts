// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";
import type { SupervisorPlan, Workflow } from "@/types/workflow";

export async function generatePlan(
  goal: string,
  llmProvider?: string,
  maxCredits?: number
): Promise<SupervisorPlan> {
  return api.post("/workflows/supervisor/plan", {
    goal,
    llm_provider: llmProvider,
    max_credits: maxCredits,
  });
}

export async function replan(
  goal: string,
  feedback: string,
  previousPlanId: string
): Promise<SupervisorPlan> {
  return api.post("/workflows/supervisor/replan", {
    goal,
    feedback,
    previous_plan_id: previousPlanId,
  });
}

export async function approvePlan(
  planId: string,
  workflowName?: string
): Promise<Workflow> {
  return api.post("/workflows/supervisor/approve", {
    plan_id: planId,
    workflow_name: workflowName,
  });
}
