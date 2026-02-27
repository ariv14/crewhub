import { api } from "../api-client";

export interface LLMKeyCreate {
  provider: string;
  api_key: string;
  model?: string;
}

export interface LLMKeyResponse {
  id: string;
  provider: string;
  model: string;
  created_at: string;
}

export async function listLLMKeys(): Promise<LLMKeyResponse[]> {
  return api.get("/llm-keys/");
}

export async function createLLMKey(data: LLMKeyCreate): Promise<LLMKeyResponse> {
  return api.post("/llm-keys/", data);
}

export async function deleteLLMKey(id: string): Promise<void> {
  return api.delete(`/llm-keys/${id}`);
}
