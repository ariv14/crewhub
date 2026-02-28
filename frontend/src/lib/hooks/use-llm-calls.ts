import { useQuery } from "@tanstack/react-query";
import * as llmCallsApi from "../api/llm-calls";

export function useLLMCalls(params?: Parameters<typeof llmCallsApi.listLLMCalls>[0]) {
  return useQuery({
    queryKey: ["llm-calls", params],
    queryFn: () => llmCallsApi.listLLMCalls(params),
  });
}

export function useLLMCall(id: string) {
  return useQuery({
    queryKey: ["llm-calls", id],
    queryFn: () => llmCallsApi.getLLMCall(id),
    enabled: !!id,
  });
}
