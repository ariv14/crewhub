// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";
import type {
  WebhookLogListResponse,
  WebhookLogDetail,
} from "@/types/webhook";

export interface WebhookLogParams {
  page?: number;
  per_page?: number;
  direction?: "inbound" | "outbound";
  method?: string;
  success?: boolean;
}

export async function listWebhookLogs(
  agentId: string,
  params?: WebhookLogParams
): Promise<WebhookLogListResponse> {
  const search = new URLSearchParams();
  if (params?.page) search.set("page", String(params.page));
  if (params?.per_page) search.set("per_page", String(params.per_page));
  if (params?.direction) search.set("direction", params.direction);
  if (params?.method) search.set("method", params.method);
  if (params?.success !== undefined) search.set("success", String(params.success));
  const qs = search.toString();
  return api.get(`/agents/${agentId}/webhook-logs/${qs ? `?${qs}` : ""}`);
}

export async function getWebhookLog(
  agentId: string,
  logId: string
): Promise<WebhookLogDetail> {
  return api.get(`/agents/${agentId}/webhook-logs/${logId}`);
}
