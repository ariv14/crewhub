import { api } from "../api-client";
import type {
  Agent,
  AgentCreate,
  AgentUpdate,
  AgentListResponse,
  AgentCardResponse,
} from "@/types/agent";

export async function listAgents(params?: {
  page?: number;
  per_page?: number;
  category?: string;
  status?: string;
  owner_id?: string;
}): Promise<AgentListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  if (params?.category) searchParams.set("category", params.category);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.owner_id) searchParams.set("owner_id", params.owner_id);
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

export async function getAgentCard(id: string): Promise<AgentCardResponse> {
  return api.get(`/agents/${id}/a2a-card`);
}

export interface AgentStatsResponse {
  daily_tasks: { date: string; count: number }[];
}

export async function getAgentStats(id: string): Promise<AgentStatsResponse> {
  return api.get(`/agents/${id}/stats`);
}
