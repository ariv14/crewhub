// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as workflowsApi from "../api/workflows";
import { useAuth } from "@/lib/auth-context";
import type {
  WorkflowCreate,
  WorkflowUpdate,
  WorkflowRunRequest,
} from "@/types/workflow";

export function useMyWorkflows() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["workflows", "mine"],
    queryFn: () => workflowsApi.listMyWorkflows(),
    enabled: !!user,
  });
}

export function usePublicWorkflows() {
  return useQuery({
    queryKey: ["workflows", "public"],
    queryFn: () => workflowsApi.listPublicWorkflows(),
  });
}

export function useWorkflow(id: string) {
  return useQuery({
    queryKey: ["workflows", id],
    queryFn: () => workflowsApi.getWorkflow(id),
    enabled: !!id && id !== "__fallback",
  });
}

export function useCreateWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: WorkflowCreate) => workflowsApi.createWorkflow(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
}

export function useUpdateWorkflow(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: WorkflowUpdate) =>
      workflowsApi.updateWorkflow(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workflows", id] });
      qc.invalidateQueries({ queryKey: ["workflows", "mine"] });
    },
  });
}

export function useDeleteWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => workflowsApi.deleteWorkflow(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
}

export function useCloneWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => workflowsApi.cloneWorkflow(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows", "mine"] }),
  });
}

export function useRunWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WorkflowRunRequest }) =>
      workflowsApi.runWorkflow(id, data),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({
        queryKey: ["workflows", variables.id, "runs"],
      });
    },
  });
}

export function useWorkflowRuns(workflowId: string) {
  return useQuery({
    queryKey: ["workflows", workflowId, "runs"],
    queryFn: () => workflowsApi.listWorkflowRuns(workflowId),
    enabled: !!workflowId && workflowId !== "__fallback",
    refetchInterval: (query) => {
      const runs = query.state.data?.runs;
      if (runs?.some((r) => r.status === "running")) return 3000;
      return false;
    },
  });
}

export function useWorkflowRun(runId: string) {
  return useQuery({
    queryKey: ["workflow-runs", runId],
    queryFn: () => workflowsApi.getWorkflowRun(runId),
    enabled: !!runId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && data.status === "running") return 3000;
      return false;
    },
  });
}

export function useCancelWorkflowRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => workflowsApi.cancelWorkflowRun(runId),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["workflow-runs", data.id] });
    },
  });
}

export function useCancelStepRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, stepRunId }: { runId: string; stepRunId: string }) =>
      workflowsApi.cancelStepRun(runId, stepRunId),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["workflow-runs", data.id] });
      qc.invalidateQueries({ queryKey: ["workflows"] });
    },
  });
}

export function useConvertCrewToWorkflow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (crewId: string) =>
      workflowsApi.convertCrewToWorkflow(crewId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
}
