// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as crewsApi from "../api/crews";
import { useAuth } from "@/lib/auth-context";
import type { CrewCreate, CrewUpdate, CrewRunRequest } from "@/types/crew";

export function useMyCrews() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["crews", "mine"],
    queryFn: () => crewsApi.listMyCrews(),
    enabled: !!user,
  });
}

export function usePublicCrews() {
  return useQuery({
    queryKey: ["crews", "public"],
    queryFn: () => crewsApi.listPublicCrews(),
  });
}

export function useCrew(id: string) {
  return useQuery({
    queryKey: ["crews", id],
    queryFn: () => crewsApi.getCrew(id),
    enabled: !!id && id !== "__fallback",
  });
}

export function useCreateCrew() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CrewCreate) => crewsApi.createCrew(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crews"] }),
  });
}

export function useUpdateCrew(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CrewUpdate) => crewsApi.updateCrew(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["crews", id] });
      qc.invalidateQueries({ queryKey: ["crews", "mine"] });
    },
  });
}

export function useDeleteCrew() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => crewsApi.deleteCrew(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crews"] }),
  });
}

export function useRunCrew() {
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CrewRunRequest }) =>
      crewsApi.runCrew(id, data),
  });
}

export function useCloneCrew() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => crewsApi.cloneCrew(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crews", "mine"] }),
  });
}
