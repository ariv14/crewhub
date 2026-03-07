export interface WebhookLog {
  id: string;
  agent_id: string;
  task_id: string | null;
  direction: "inbound" | "outbound";
  method: string;
  status_code: number | null;
  success: boolean;
  error_message: string | null;
  latency_ms: number | null;
  created_at: string;
}

export interface WebhookLogDetail extends WebhookLog {
  request_body: Record<string, unknown> | null;
  response_body: Record<string, unknown> | null;
}

export interface WebhookLogListResponse {
  logs: WebhookLog[];
  total: number;
  page: number;
  per_page: number;
}
