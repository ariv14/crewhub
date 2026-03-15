// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";
import type {
  Balance,
  SpendByAgentResponse,
  TransactionListResponse,
  UsageResponse,
} from "@/types/credits";

export async function getBalance(): Promise<Balance> {
  return api.get("/credits/balance");
}

export async function purchaseCredits(amount: number): Promise<Balance> {
  return api.post("/credits/purchase", { amount });
}

export async function listTransactions(params?: {
  page?: number;
  per_page?: number;
}): Promise<TransactionListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  const qs = searchParams.toString();
  return api.get(`/credits/transactions${qs ? `?${qs}` : ""}`);
}

export async function getUsage(period?: string): Promise<UsageResponse> {
  const qs = period ? `?period=${period}` : "";
  return api.get(`/credits/usage${qs}`);
}

export async function getSpendByAgent(
  period?: string
): Promise<SpendByAgentResponse> {
  const qs = period ? `?period=${period}` : "";
  return api.get(`/credits/spend-by-agent${qs}`);
}
