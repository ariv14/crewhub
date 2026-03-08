export type TaskStatus =
  | "submitted"
  | "pending_approval"
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
  confirmed?: boolean;
  suggested_agent_id?: string;
  suggestion_confidence?: number;
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
  quality_score: number | null;
  eval_model: string | null;
  eval_relevance: number | null;
  eval_completeness: number | null;
  eval_coherence: number | null;
  delegation_warning: string | null;
  delegation_depth: number;
  parent_task_id: string | null;
  suggested_agent_id: string | null;
  suggestion_confidence: number | null;
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

export interface SuggestionRequest {
  message: string;
  category?: string;
  tags?: string[];
  max_credits?: number;
  limit?: number;
}

export interface SkillSuggestion {
  agent: {
    id: string;
    name: string;
    description: string;
    version: string;
    category: string;
    reputation_score: number;
    avg_latency_ms: number | null;
    total_tasks: number;
    skills: { id: string; name: string; description: string }[];
    pricing?: {
      tiers: { credits_per_unit: number; name: string; is_default: boolean }[];
      credits: number;
    };
  };
  skill: {
    id: string;
    name: string;
    description: string;
  };
  confidence: number;
  reason: string;
  low_confidence: boolean;
}

export interface SuggestionResponse {
  suggestions: SkillSuggestion[];
  fallback_used: boolean;
  hint: string | null;
}

