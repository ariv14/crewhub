import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as customAgentsApi from "../api/custom-agents";
import { useAuth } from "../auth-context";
import type {
  CreateAgentRequest,
  TryAgentRequest,
  VoteRequest,
} from "@/types/custom-agent";

export function useCustomAgents(params?: Parameters<typeof customAgentsApi.listCustomAgents>[0]) {
  return useQuery({
    queryKey: ["custom-agents", params],
    queryFn: () => customAgentsApi.listCustomAgents(params),
  });
}

export function useCustomAgent(id: string) {
  return useQuery({
    queryKey: ["custom-agents", id],
    queryFn: () => customAgentsApi.getCustomAgent(id),
    enabled: !!id && id !== "__fallback",
    retry: 1,
  });
}

export function useCreateCustomAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateAgentRequest) => customAgentsApi.createCustomAgent(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["custom-agents"] }),
  });
}

export function useTryCustomAgent(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TryAgentRequest) => customAgentsApi.tryCustomAgent(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["custom-agents", id] });
      qc.invalidateQueries({ queryKey: ["custom-agents"] });
    },
  });
}

export function useVoteCustomAgent(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: VoteRequest) => customAgentsApi.voteCustomAgent(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["custom-agents", id] });
      qc.invalidateQueries({ queryKey: ["custom-agents"] });
    },
  });
}
