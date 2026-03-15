// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";

export interface LLMCallSummary {
  id: string;
  agent_id: string | null;
  task_id: string | null;
  provider: string;
  model: string;
  status_code: number | null;
  latency_ms: number | null;
  tokens_input: number | null;
  tokens_output: number | null;
  error_message: string | null;
  created_at: string;
}

export interface LLMCallDetail extends LLMCallSummary {
  request_body: Record<string, unknown> | null;
  response_body: Record<string, unknown> | null;
}

export interface LLMCallListResponse {
  calls: LLMCallSummary[];
  total: number;
  page: number;
  per_page: number;
}

export async function listLLMCalls(params?: {
  page?: number;
  per_page?: number;
  agent_id?: string;
  status_code?: number;
  provider?: string;
}): Promise<LLMCallListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  if (params?.agent_id) searchParams.set("agent_id", params.agent_id);
  if (params?.status_code) searchParams.set("status_code", String(params.status_code));
  if (params?.provider) searchParams.set("provider", params.provider);
  const qs = searchParams.toString();
  return api.get(`/admin/llm-calls/${qs ? `?${qs}` : ""}`);
}

export async function getLLMCall(id: string): Promise<LLMCallDetail> {
  return api.get(`/admin/llm-calls/${id}`);
}
