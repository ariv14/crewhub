import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as tasksApi from "../api/tasks";
import type { TaskCreate, TaskRating } from "@/types/task";

export function useTasks(params?: Parameters<typeof tasksApi.listTasks>[0]) {
  return useQuery({
    queryKey: ["tasks", params],
    queryFn: () => tasksApi.listTasks(params),
  });
}

export function useTask(id: string) {
  return useQuery({
    queryKey: ["tasks", id],
    queryFn: () => tasksApi.getTask(id),
    enabled: !!id,
    refetchInterval: 5000, // Poll for status updates
  });
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskCreate) => tasksApi.createTask(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });
}

export function useCancelTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => tasksApi.cancelTask(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ["tasks", id] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useRateTask(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskRating) => tasksApi.rateTask(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks", id] }),
  });
}

export function useSendMessage(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (message: Parameters<typeof tasksApi.sendMessage>[1]) =>
      tasksApi.sendMessage(id, message),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks", id] }),
  });
}
