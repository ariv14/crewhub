import type { Agent } from "./agent";

export type SearchMode = "keyword" | "semantic" | "capability" | "intent";

export interface SearchQuery {
  query: string;
  mode: SearchMode;
  category?: string;
  tags: string[];
  max_latency_ms?: number;
  max_credits?: number;
  input_modes: string[];
  output_modes: string[];
  min_reputation: number;
  limit: number;
}

export interface AgentMatch {
  agent: Agent;
  relevance_score: number;
  match_reason: string;
}

export interface DiscoveryResponse {
  matches: AgentMatch[];
  total_candidates: number;
  query_time_ms: number;
}
