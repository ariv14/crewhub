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

export function useDeleteAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agentsApi.deleteAgent(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });
}
