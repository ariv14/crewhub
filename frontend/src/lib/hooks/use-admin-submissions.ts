// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as adminApi from "../api/admin-submissions";
import { useAuth } from "../auth-context";

export function useAdminSubmissions(status = "pending_review", page = 1, perPage = 20) {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["admin", "submissions", status, page, perPage],
    queryFn: () => adminApi.listAdminSubmissions(status, page, perPage),
    enabled: !!user,
  });
}

export function useApproveSubmission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminApi.approveSubmission(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "submissions"] });
    },
  });
}

export function useRejectSubmission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes: string }) => adminApi.rejectSubmission(id, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "submissions"] });
    },
  });
}

export function useRevokeSubmission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminApi.revokeSubmission(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "submissions"] });
    },
  });
}
