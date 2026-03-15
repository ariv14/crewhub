// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as adminApi from "../api/admin";

export function useAdminStats() {
  return useQuery({
    queryKey: ["admin", "stats"],
    queryFn: adminApi.getStats,
    refetchInterval: 30_000,
  });
}

export function useAdminUsers(params?: Parameters<typeof adminApi.listUsers>[0]) {
  return useQuery({
    queryKey: ["admin", "users", params],
    queryFn: () => adminApi.listUsers(params),
  });
}

export function useUpdateUserStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: { is_active?: boolean; is_admin?: boolean } }) =>
      adminApi.updateUserStatus(userId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
      qc.invalidateQueries({ queryKey: ["admin", "stats"] });
    },
  });
}

export function useAdminTasks(params?: Parameters<typeof adminApi.listAllTasks>[0]) {
  return useQuery({
    queryKey: ["admin", "tasks", params],
    queryFn: () => adminApi.listAllTasks(params),
    refetchInterval: 5_000,
  });
}

export function useAdminTransactions(params?: Parameters<typeof adminApi.listAllTransactions>[0]) {
  return useQuery({
    queryKey: ["admin", "transactions", params],
    queryFn: () => adminApi.listAllTransactions(params),
  });
}

export function useUpdateAgentStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ agentId, status }: { agentId: string; status: string }) =>
      adminApi.updateAgentStatus(agentId, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents"] });
      qc.invalidateQueries({ queryKey: ["admin", "stats"] });
    },
  });
}
