// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useMutation } from "@tanstack/react-query";
import { generatePlan, replan, approvePlan } from "@/lib/api/supervisor";

export function useSupervisorPlan() {
  return useMutation({
    mutationFn: (data: {
      goal: string;
      llmProvider?: string;
      maxCredits?: number;
    }) => generatePlan(data.goal, data.llmProvider, data.maxCredits),
  });
}

export function useSupervisorReplan() {
  return useMutation({
    mutationFn: (data: {
      goal: string;
      feedback: string;
      previousPlanId: string;
    }) => replan(data.goal, data.feedback, data.previousPlanId),
  });
}

export function useApprovePlan() {
  return useMutation({
    mutationFn: (data: { planId: string; workflowName?: string }) =>
      approvePlan(data.planId, data.workflowName),
  });
}
