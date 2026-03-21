// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";
import type { User } from "@/types/auth";
import type { Agent } from "@/types/agent";
import type { Task } from "@/types/task";
import type { Transaction } from "@/types/credits";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PlatformStats {
  total_users: number;
  active_users: number;
  total_agents: number;
  active_agents: number;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  total_transaction_volume: number;
}

export interface AdminUserListResponse {
  users: User[];
  total: number;
}

export interface AdminTaskListResponse {
  tasks: Task[];
  total: number;
}

export interface AdminTransactionListResponse {
  transactions: Transaction[];
  total: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function getStats(): Promise<PlatformStats> {
  return api.get("/admin/stats");
}

export async function listUsers(params?: {
  page?: number;
  per_page?: number;
}): Promise<AdminUserListResponse> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.per_page) qs.set("per_page", String(params.per_page));
  const query = qs.toString();
  return api.get(`/admin/users/${query ? `?${query}` : ""}`);
}

export async function updateUserStatus(
  userId: string,
  data: { is_active?: boolean; is_admin?: boolean }
): Promise<User> {
  return api.put(`/admin/users/${userId}/status`, data);
}

export async function listAllTasks(params?: {
  page?: number;
  per_page?: number;
  status?: string;
}): Promise<AdminTaskListResponse> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.per_page) qs.set("per_page", String(params.per_page));
  if (params?.status) qs.set("status", params.status);
  const query = qs.toString();
  return api.get(`/admin/tasks/${query ? `?${query}` : ""}`);
}

export async function listAllTransactions(params?: {
  page?: number;
  per_page?: number;
  type?: string;
}): Promise<AdminTransactionListResponse> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.per_page) qs.set("per_page", String(params.per_page));
  if (params?.type) qs.set("type", params.type);
  const query = qs.toString();
  return api.get(`/admin/transactions/${query ? `?${query}` : ""}`);
}

export async function updateAgentStatus(
  agentId: string,
  status: string
): Promise<Agent> {
  return api.put(`/admin/agents/${agentId}/status`, { status });
}

export async function updateAgentVerification(
  agentId: string,
  level: string
): Promise<Agent> {
  return api.put(`/admin/agents/${agentId}/verification`, { verification_level: level });
}

export async function grantCredits(
  userId: string,
  amount: number,
  reason: string
): Promise<unknown> {
  return api.post("/admin/credits/grant", { user_id: userId, amount, reason });
}
