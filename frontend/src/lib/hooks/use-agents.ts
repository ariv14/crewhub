import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as agentsApi from "../api/agents";
import type { AgentCreate, AgentUpdate } from "@/types/agent";

export function useAgents(params?: Parameters<typeof agentsApi.listAgents>[0]) {
  return useQuery({
    queryKey: ["agents", params],
    queryFn: () => agentsApi.listAgents(params),
  });
}

export function useAgent(id: string) {
  return useQuery({
    queryKey: ["agents", id],
    queryFn: () => agentsApi.getAgent(id),
    enabled: !!id,
  });
}

export function useAgentCard(id: string) {
  return useQuery({
    queryKey: ["agents", id, "a2a-card"],
    queryFn: () => agentsApi.getAgentCard(id),
    enabled: !!id,
  });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AgentCreate) => agentsApi.createAgent(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });
}

export function useUpdateAgent(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AgentUpdate) => agentsApi.updateAgent(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents", id] });
      qc.invalidateQueries({ queryKey: ["agents"] });
    },
  });
}

export function useAgentStats(id: string) {
  return useQuery({
    queryKey: ["agents", id, "stats"],
    queryFn: () => agentsApi.getAgentStats(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

export function useDetectAgent() {
  return useMutation({
    mutationFn: (url: string) => agentsApi.detectAgent(url),
  });
}

export function useDeleteAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agentsApi.deleteAgent(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });
}

export function useDeleteAgentPermanently() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agentsApi.deleteAgentPermanently(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });
}
