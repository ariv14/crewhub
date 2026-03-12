import type { Agent, Skill } from "./agent";

export interface WorkflowStep {
  id: string;
  workflow_id: string;
  agent_id: string;
  skill_id: string;
  step_group: number;
  position: number;
  input_mode: "chain" | "original" | "custom";
  input_template: string | null;
  instructions: string | null;
  label: string | null;
  agent: Agent;
  skill: Skill;
}

export interface Workflow {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  icon: string;
  is_public: boolean;
  max_total_credits: number | null;
  timeout_seconds: number | null;
  step_timeout_seconds: number | null;
  steps: WorkflowStep[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowCreate {
  name: string;
  description?: string;
  icon?: string;
  is_public?: boolean;
  max_total_credits?: number;
  timeout_seconds?: number;
  step_timeout_seconds?: number;
  steps: {
    agent_id: string;
    skill_id: string;
    step_group: number;
    position: number;
    input_mode?: string;
    input_template?: string;
    instructions?: string;
    label?: string;
  }[];
}

export interface WorkflowUpdate {
  name?: string;
  description?: string;
  icon?: string;
  is_public?: boolean;
  max_total_credits?: number;
  timeout_seconds?: number;
  step_timeout_seconds?: number;
  steps?: WorkflowCreate["steps"];
}

export interface WorkflowListResponse {
  workflows: Workflow[];
  total: number;
}

export interface WorkflowRunRequest {
  message: string;
}

export interface WorkflowStepRun {
  id: string;
  run_id: string;
  step_id: string | null;
  task_id: string | null;
  step_group: number;
  status: "pending" | "running" | "completed" | "failed";
  output_text: string | null;
  error: string | null;
  credits_charged: number | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  user_id: string;
  schedule_id: string | null;
  status: "running" | "completed" | "failed" | "canceled";
  current_step_group: number;
  input_message: string;
  workflow_snapshot: Record<string, unknown> | null;
  total_credits_charged: number | null;
  error: string | null;
  step_runs: WorkflowStepRun[];
  created_at: string;
  completed_at: string | null;
}

export interface WorkflowRunListResponse {
  runs: WorkflowRun[];
  total: number;
}
