// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";
import type {
  Workflow,
  WorkflowCreate,
  WorkflowListResponse,
  WorkflowRun,
  WorkflowRunListResponse,
  WorkflowRunRequest,
  WorkflowUpdate,
} from "@/types/workflow";

export async function listMyWorkflows(): Promise<WorkflowListResponse> {
  return api.get("/workflows/");
}

export async function listPublicWorkflows(): Promise<WorkflowListResponse> {
  return api.get("/workflows/public");
}

export async function getWorkflow(id: string): Promise<Workflow> {
  return api.get(`/workflows/${id}`);
}

export async function createWorkflow(data: WorkflowCreate): Promise<Workflow> {
  return api.post("/workflows/", data);
}

export async function updateWorkflow(
  id: string,
  data: WorkflowUpdate
): Promise<Workflow> {
  return api.put(`/workflows/${id}`, data);
}

export async function deleteWorkflow(id: string): Promise<void> {
  return api.delete(`/workflows/${id}`);
}

export async function cloneWorkflow(id: string): Promise<Workflow> {
  return api.post(`/workflows/${id}/clone`, {});
}

export async function runWorkflow(
  id: string,
  data: WorkflowRunRequest
): Promise<WorkflowRun> {
  return api.post(`/workflows/${id}/run`, data);
}

export async function listWorkflowRuns(
  id: string
): Promise<WorkflowRunListResponse> {
  return api.get(`/workflows/${id}/runs`);
}

export async function getWorkflowRun(runId: string): Promise<WorkflowRun> {
  return api.get(`/workflows/runs/${runId}`);
}

export async function cancelWorkflowRun(runId: string): Promise<WorkflowRun> {
  return api.post(`/workflows/runs/${runId}/cancel`, {});
}

export interface WorkflowRunOutput {
  run_id: string;
  workflow_id: string;
  status: string;
  input_message: string;
  final_output: string | null;
  step_outputs: {
    step_run_id: string;
    step_group: number;
    label: string;
    status: string;
    output_text: string | null;
    error: string | null;
    credits_charged: number | null;
  }[];
  total_credits_charged: number | null;
  created_at: string | null;
  completed_at: string | null;
}

export async function getWorkflowRunOutput(
  runId: string
): Promise<WorkflowRunOutput> {
  return api.get(`/workflows/runs/${runId}/output`);
}

export async function cancelStepRun(
  runId: string,
  stepRunId: string
): Promise<WorkflowRun> {
  return api.post(`/workflows/runs/${runId}/steps/${stepRunId}/cancel`, {});
}

export async function convertCrewToWorkflow(
  crewId: string
): Promise<Workflow> {
  return api.post(`/workflows/from-crew/${crewId}`, {});
}
