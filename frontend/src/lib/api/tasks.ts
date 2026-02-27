import { api } from "../api-client";
import type {
  Task,
  TaskCreate,
  TaskRating,
  TaskListResponse,
} from "@/types/task";

export async function listTasks(params?: {
  page?: number;
  per_page?: number;
  status?: string;
}): Promise<TaskListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  if (params?.status) searchParams.set("status", params.status);
  const qs = searchParams.toString();
  return api.get(`/tasks/${qs ? `?${qs}` : ""}`);
}

export async function getTask(id: string): Promise<Task> {
  return api.get(`/tasks/${id}`);
}

export async function createTask(data: TaskCreate): Promise<Task> {
  return api.post("/tasks/", data);
}

export async function cancelTask(id: string): Promise<Task> {
  return api.post(`/tasks/${id}/cancel`);
}

export async function rateTask(id: string, data: TaskRating): Promise<Task> {
  return api.post(`/tasks/${id}/rate`, data);
}

export async function sendMessage(
  id: string,
  message: { role: string; parts: { type: string; content: string }[] }
): Promise<Task> {
  return api.post(`/tasks/${id}/message`, message);
}

export async function submitX402Receipt(
  taskId: string,
  receipt: {
    tx_hash: string;
    chain: string;
    token: string;
    amount: number;
    payer: string;
    payee: string;
  }
): Promise<{ verified: boolean; task_status: string }> {
  return api.post(`/tasks/${taskId}/x402-receipt`, receipt);
}
