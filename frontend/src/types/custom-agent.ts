export type CustomAgentStatus = "active" | "promoted" | "archived";

export interface CustomAgent {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[] | null;
  source_query: string;
  status: CustomAgentStatus;
  try_count: number;
  completion_count: number;
  avg_rating: number;
  upvote_count: number;
  promoted_agent_id: string | null;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  user_vote: number | null;
}

export interface CustomAgentListResponse {
  agents: CustomAgent[];
  total: number;
}

export interface CreateAgentRequest {
  message: string;
  category?: string;
  auto_execute?: boolean;
}

export interface CreateAgentResponse {
  agent: CustomAgent;
  task_id: string | null;
  task_status: string | null;
  result: string | null;
}

export interface TryAgentRequest {
  message: string;
}

export interface VoteRequest {
  vote: number;
}

export interface AgentRequest {
  id: string;
  user_id: string | null;
  query: string;
  best_match_confidence: number | null;
  custom_agent_id: string | null;
  created_at: string;
}

export interface AgentRequestListResponse {
  requests: AgentRequest[];
  total: number;
}
