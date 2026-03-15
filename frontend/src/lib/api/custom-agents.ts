// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";
import type {
  CreateAgentRequest,
  CreateAgentResponse,
  CustomAgent,
  CustomAgentListResponse,
  TryAgentRequest,
  VoteRequest,
} from "@/types/custom-agent";

export async function createCustomAgent(
  data: CreateAgentRequest
): Promise<CreateAgentResponse> {
  return api.post("/custom-agents/create", data);
}

export async function listCustomAgents(params?: {
  sort?: string;
  category?: string;
  page?: number;
  per_page?: number;
}): Promise<CustomAgentListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.sort) searchParams.set("sort", params.sort);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  const qs = searchParams.toString();
  return api.get(`/custom-agents/${qs ? `?${qs}` : ""}`);
}

export async function getCustomAgent(id: string): Promise<CustomAgent> {
  return api.get(`/custom-agents/${id}`);
}

export async function tryCustomAgent(
  id: string,
  data: TryAgentRequest
): Promise<CreateAgentResponse> {
  return api.post(`/custom-agents/${id}/try`, data);
}

export async function voteCustomAgent(
  id: string,
  data: VoteRequest
): Promise<CustomAgent> {
  return api.post(`/custom-agents/${id}/vote`, data);
}
