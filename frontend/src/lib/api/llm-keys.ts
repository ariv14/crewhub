// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";

export interface LLMKeyInfo {
  provider: string;
  is_set: boolean;
  masked_key: string;
}

export interface LLMKeysListResponse {
  keys: LLMKeyInfo[];
}

export async function listLLMKeys(): Promise<LLMKeysListResponse> {
  return api.get("/llm-keys/");
}

export async function setLLMKey(
  provider: string,
  apiKey: string
): Promise<LLMKeyInfo> {
  return api.put(`/llm-keys/${provider}`, {
    provider,
    api_key: apiKey,
  });
}

export async function deleteLLMKey(provider: string): Promise<void> {
  return api.delete(`/llm-keys/${provider}`);
}
