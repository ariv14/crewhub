// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as builderApi from "../api/builder";
import { useAuth } from "../auth-context";

export function useSubmissions(page = 1, perPage = 20) {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["builder", "submissions", page, perPage],
    queryFn: () => builderApi.listSubmissions(page, perPage),
    enabled: !!user,
  });
}

export function useCreateSubmission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: builderApi.SubmissionCreate) => builderApi.createSubmission(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["builder", "submissions"] });
    },
  });
}

export function useDeleteSubmission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => builderApi.deleteSubmission(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["builder", "submissions"] });
    },
  });
}

export function useResubmitSubmission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: builderApi.SubmissionResubmit }) =>
      builderApi.resubmitSubmission(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["builder", "submissions"] });
    },
  });
}
