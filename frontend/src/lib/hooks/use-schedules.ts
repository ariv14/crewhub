import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as schedulesApi from "../api/schedules";
import { useAuth } from "@/lib/auth-context";
import type { ScheduleCreate, ScheduleUpdate } from "@/types/schedule";

export function useMySchedules() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["schedules", "mine"],
    queryFn: () => schedulesApi.listMySchedules(),
    enabled: !!user,
  });
}

export function useSchedule(id: string) {
  return useQuery({
    queryKey: ["schedules", id],
    queryFn: () => schedulesApi.getSchedule(id),
    enabled: !!id && id !== "__fallback",
  });
}

export function useCreateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ScheduleCreate) => schedulesApi.createSchedule(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules"] }),
  });
}

export function useUpdateSchedule(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ScheduleUpdate) =>
      schedulesApi.updateSchedule(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["schedules", id] });
      qc.invalidateQueries({ queryKey: ["schedules", "mine"] });
    },
  });
}

export function useDeleteSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => schedulesApi.deleteSchedule(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules"] }),
  });
}

export function usePauseSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => schedulesApi.pauseSchedule(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["schedules", id] });
      qc.invalidateQueries({ queryKey: ["schedules", "mine"] });
    },
  });
}

export function useResumeSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => schedulesApi.resumeSchedule(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["schedules", id] });
      qc.invalidateQueries({ queryKey: ["schedules", "mine"] });
    },
  });
}
