// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useQuery } from "@tanstack/react-query";
import { listWebhookLogs, getWebhookLog } from "@/lib/api/webhooks";
import type { WebhookLogParams } from "@/lib/api/webhooks";

export function useWebhookLogs(agentId: string | undefined, params?: WebhookLogParams) {
  return useQuery({
    queryKey: ["webhook-logs", agentId, params],
    queryFn: () => listWebhookLogs(agentId!, params),
    enabled: !!agentId,
    staleTime: 30_000, // 30s — logs don't change frequently
  });
}

export function useWebhookLogDetail(agentId: string | undefined, logId: string | undefined) {
  return useQuery({
    queryKey: ["webhook-log", agentId, logId],
    queryFn: () => getWebhookLog(agentId!, logId!),
    enabled: !!agentId && !!logId,
  });
}
