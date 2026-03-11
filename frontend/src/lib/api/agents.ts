import { api } from "../api-client";
import type {
  Agent,
  AgentCreate,
  AgentUpdate,
  AgentListResponse,
  AgentCardResponse,
  DetectResponse,
} from "@/types/agent";

export async function listAgents(params?: {
  page?: number;
  per_page?: number;
  category?: string;
  status?: string;
  owner_id?: string;
  q?: string;
}): Promise<AgentListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  if (params?.category) searchParams.set("category", params.category);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.owner_id) searchParams.set("owner_id", params.owner_id);
  if (params?.q) searchParams.set("q", params.q);
  const qs = searchParams.toString();
  return api.get(`/agents/${qs ? `?${qs}` : ""}`);
}

export async function getAgent(id: string): Promise<Agent> {
  return api.get(`/agents/${id}`);
}

export async function createAgent(data: AgentCreate): Promise<Agent> {
  return api.post("/agents/", data);
}

export async function updateAgent(
  id: string,
  data: AgentUpdate
): Promise<Agent> {
  return api.put(`/agents/${id}`, data);
}

export async function deleteAgent(id: string): Promise<void> {
  return api.delete(`/agents/${id}`);
}

export async function deleteAgentPermanently(id: string): Promise<void> {
  return api.delete(`/agents/${id}/permanent`);
}

export async function getAgentCard(id: string): Promise<AgentCardResponse> {
  return api.get(`/agents/${id}/card`);
}

export interface AgentStatsResponse {
  daily_tasks: { date: string; count: number }[];
}

export async function getAgentStats(id: string): Promise<AgentStatsResponse> {
  return api.get(`/agents/${id}/stats`);
}

export async function detectAgent(url: string): Promise<DetectResponse> {
  return api.post("/agents/detect", { url });
}

export async function requestVerification(id: string): Promise<Agent> {
  return api.post(`/agents/${id}/verify`, {});
}

// --- Analytics / Eval Trends ---

export interface WeeklyTrend {
  week: string;
  avg_quality: number | null;
  avg_relevance: number | null;
  avg_completeness: number | null;
  avg_coherence: number | null;
  avg_rating: number | null;
  rating_count: number;
  success_rate: number | null;
  avg_latency_ms: number | null;
  task_count: number;
}

export interface AgentTrendsResponse {
  agent_id: string;
  eval_model: string | null;
  trends: WeeklyTrend[];
}

export interface EvalModelInfo {
  id: string;
  name: string;
  provider: string;
  credits_per_eval: number;
  is_default: boolean;
}

export async function getEvalModels(): Promise<{ models: EvalModelInfo[] }> {
  return api.get("/analytics/eval-models");
}

export async function getAgentTrends(
  id: string,
  weeks = 8
): Promise<AgentTrendsResponse> {
  return api.get(`/analytics/agent/${id}/trends?weeks=${weeks}`);
}

export interface PublicStats {
  total_agents: number;
  total_skills: number;
  total_categories: number;
  tasks_completed: number;
  avg_success_rate: number | null;
  credits_earned_by_builders: number;
}

export async function getPublicStats(): Promise<PublicStats> {
  return api.get("/analytics/public-stats");
}
