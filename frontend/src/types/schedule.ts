export interface Schedule {
  id: string;
  owner_id: string;
  name: string;
  schedule_type: "single_task" | "workflow" | "crew";
  target_id: string | null;
  task_params: Record<string, string> | null;
  cron_expression: string;
  timezone: string;
  input_message: string | null;
  is_active: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  run_count: number;
  max_runs: number | null;
  consecutive_failures: number;
  max_consecutive_failures: number;
  credit_minimum: number;
  created_at: string;
}

export interface ScheduleCreate {
  name: string;
  schedule_type: "single_task" | "workflow" | "crew";
  target_id?: string;
  task_params?: Record<string, string>;
  cron_expression: string;
  timezone?: string;
  input_message?: string;
  is_active?: boolean;
  max_runs?: number;
  credit_minimum?: number;
}

export interface ScheduleUpdate {
  name?: string;
  cron_expression?: string;
  timezone?: string;
  input_message?: string;
  is_active?: boolean;
  max_runs?: number;
  credit_minimum?: number;
  max_consecutive_failures?: number;
}

export interface ScheduleListResponse {
  schedules: Schedule[];
  total: number;
}
