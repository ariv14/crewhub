export type TaskStatus =
  | "submitted"
  | "pending_payment"
  | "working"
  | "input_required"
  | "completed"
  | "failed"
  | "canceled"
  | "rejected";

export type PaymentMethod = "credits" | "x402";

export interface MessagePart {
  type: string;
  content: string | null;
  data: Record<string, unknown> | null;
  mime_type: string | null;
}

export interface TaskMessage {
  role: string;
  parts: MessagePart[];
}

export interface Artifact {
  name: string | null;
  parts: MessagePart[];
  metadata: Record<string, unknown>;
}

export interface TaskCreate {
  provider_agent_id: string;
  skill_id: string;
  messages: TaskMessage[];
  max_credits?: number;
  tier?: string;
  payment_method?: PaymentMethod;
  validate_match?: boolean;
}

export interface Task {
  id: string;
  client_agent_id: string | null;
  provider_agent_id: string | null;
  provider_agent_name: string | null;
  skill_id: string | null;
  skill_name: string | null;
  status: TaskStatus;
  messages: TaskMessage[];
  artifacts: Artifact[];
  credits_quoted: number;
  credits_charged: number;
  latency_ms: number | null;
  client_rating: number | null;
  payment_method: string;
  x402_receipt: Record<string, unknown> | null;
  status_history: { status: string; at: string }[] | null;
  delegation_warning: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface TaskRating {
  score: number;
  comment: string;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
}

