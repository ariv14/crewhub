"use client";

import { useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Filter,
  Webhook,
  XCircle,
} from "lucide-react";
import { useWebhookLogs, useWebhookLogDetail } from "@/lib/hooks/use-webhooks";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatRelativeTime } from "@/lib/utils";
import { JsonViewer } from "@/components/shared/json-viewer";
import type { WebhookLog } from "@/types/webhook";

const DIRECTION_FILTERS = [
  { label: "All", value: undefined },
  { label: "Inbound", value: "inbound" },
  { label: "Outbound", value: "outbound" },
] as const;

const STATUS_FILTERS = [
  { label: "All", value: undefined },
  { label: "Success", value: true },
  { label: "Failed", value: false },
] as const;

function DirectionBadge({ direction }: { direction: string }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "text-[10px] gap-1",
        direction === "inbound"
          ? "border-blue-500/30 text-blue-500"
          : "border-purple-500/30 text-purple-500"
      )}
    >
      {direction === "inbound" ? (
        <ArrowDownLeft className="h-3 w-3" />
      ) : (
        <ArrowUpRight className="h-3 w-3" />
      )}
      {direction}
    </Badge>
  );
}

function StatusIndicator({ success }: { success: boolean }) {
  return success ? (
    <CheckCircle2 className="h-4 w-4 text-green-500" />
  ) : (
    <XCircle className="h-4 w-4 text-red-500" />
  );
}

/** Expandable row showing webhook log details with request/response payloads. */
function WebhookLogRow({
  log,
  agentId,
}: {
  log: WebhookLog;
  agentId: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const { data: detail } = useWebhookLogDetail(
    expanded ? agentId : undefined,
    expanded ? log.id : undefined
  );

  return (
    <div
      className="rounded-lg border transition-colors hover:border-primary/20"
      data-testid="webhook-log-row"
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 p-3 text-left"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
        )}

        <StatusIndicator success={log.success} />

        <DirectionBadge direction={log.direction} />

        <code className="text-xs font-medium">{log.method}</code>

        <div className="flex-1" />

        {log.latency_ms != null && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            {log.latency_ms}ms
          </span>
        )}

        {log.status_code && (
          <Badge
            variant="outline"
            className={cn(
              "text-[10px]",
              log.status_code >= 200 && log.status_code < 300
                ? "border-green-500/30 text-green-500"
                : "border-red-500/30 text-red-500"
            )}
          >
            {log.status_code}
          </Badge>
        )}

        <span className="text-xs text-muted-foreground">
          {formatRelativeTime(log.created_at)}
        </span>
      </button>

      {expanded && (
        <div className="border-t px-4 py-3 space-y-3">
          {log.error_message && (
            <div className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-500">
              {log.error_message}
            </div>
          )}

          {log.task_id && (
            <p className="text-xs text-muted-foreground">
              Task:{" "}
              <a
                href={`/dashboard/tasks/${log.task_id}/`}
                className="font-mono hover:text-primary hover:underline"
              >
                {log.task_id.slice(0, 8)}...
              </a>
            </p>
          )}

          {detail?.request_body && (
            <JsonViewer data={detail.request_body} title="Request" />
          )}
          {detail?.response_body && (
            <JsonViewer data={detail.response_body} title="Response" />
          )}

          {!detail && (
            <p className="text-xs text-muted-foreground">Loading details...</p>
          )}
        </div>
      )}
    </div>
  );
}

/** Full webhook logs viewer for an agent. */
export function WebhookLogsViewer({ agentId }: { agentId: string }) {
  const [directionFilter, setDirectionFilter] = useState<
    "inbound" | "outbound" | undefined
  >(undefined);
  const [successFilter, setSuccessFilter] = useState<boolean | undefined>(
    undefined
  );
  const [page, setPage] = useState(1);

  const { data, isLoading } = useWebhookLogs(agentId, {
    page,
    per_page: 20,
    direction: directionFilter,
    success: successFilter,
  });

  const logs = data?.logs ?? [];
  const total = data?.total ?? 0;
  const hasMore = page * 20 < total;

  return (
    <div className="space-y-4" data-testid="webhook-logs-viewer">
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Webhook className="h-5 w-5" />
          Webhook Logs
        </h2>
        <p className="text-sm text-muted-foreground">
          A2A communication history for this agent
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4" data-testid="webhook-filters">
        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">Direction:</span>
          {DIRECTION_FILTERS.map((f) => (
            <button
              key={f.label}
              onClick={() => {
                setDirectionFilter(f.value);
                setPage(1);
              }}
              className={cn(
                "rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
                directionFilter === f.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Status:</span>
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.label}
              onClick={() => {
                setSuccessFilter(f.value);
                setPage(1);
              }}
              className={cn(
                "rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
                successFilter === f.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Log entries */}
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : logs.length === 0 ? (
        <div className="rounded-lg border border-dashed py-8 text-center">
          <Webhook className="mx-auto h-8 w-8 text-muted-foreground/50" />
          <p className="mt-2 text-sm text-muted-foreground">
            No webhook logs yet
          </p>
          <p className="text-xs text-muted-foreground">
            Logs will appear when tasks are dispatched to or callbacks received
            from this agent
          </p>
        </div>
      ) : (
        <>
          <p className="text-xs text-muted-foreground">
            Showing {Math.min(page * 20, total)} of {total} log
            {total !== 1 ? "s" : ""}
          </p>
          <div className="space-y-2">
            {logs.map((log) => (
              <WebhookLogRow key={log.id} log={log} agentId={agentId} />
            ))}
          </div>

          {total > 20 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="text-xs text-muted-foreground">
                Page {page} of {Math.ceil(total / 20)}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={!hasMore}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
