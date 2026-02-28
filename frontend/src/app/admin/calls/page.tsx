"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { useLLMCalls } from "@/lib/hooks/use-llm-calls";
import { DataTable, type ColumnDef } from "@/components/shared/data-table";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import type { LLMCallSummary } from "@/lib/api/llm-calls";

const columns: ColumnDef<LLMCallSummary>[] = [
  {
    accessorKey: "created_at",
    header: "Timestamp",
    cell: ({ row }) => {
      const d = new Date(row.getValue("created_at") as string);
      return (
        <span className="text-xs">
          {d.toLocaleDateString()} {d.toLocaleTimeString()}
        </span>
      );
    },
  },
  {
    accessorKey: "provider",
    header: "Provider",
    cell: ({ row }) => (
      <Badge variant="outline" className="text-xs">
        {row.getValue("provider") as string}
      </Badge>
    ),
  },
  {
    accessorKey: "model",
    header: "Model",
    cell: ({ row }) => (
      <span className="max-w-[200px] truncate text-xs font-mono">
        {row.getValue("model") as string}
      </span>
    ),
  },
  {
    accessorKey: "status_code",
    header: "Status",
    cell: ({ row }) => {
      const code = row.getValue("status_code") as number | null;
      if (code == null) return <span className="text-xs text-muted-foreground">—</span>;
      return (
        <Badge
          variant={code >= 200 && code < 300 ? "default" : "destructive"}
          className="text-xs"
        >
          {code}
        </Badge>
      );
    },
  },
  {
    accessorKey: "latency_ms",
    header: "Latency",
    cell: ({ row }) => {
      const ms = row.getValue("latency_ms") as number | null;
      return <span className="text-xs">{ms != null ? `${ms}ms` : "—"}</span>;
    },
  },
  {
    accessorKey: "tokens_input",
    header: "In Tokens",
    cell: ({ row }) => {
      const t = row.getValue("tokens_input") as number | null;
      return <span className="text-xs">{t ?? "—"}</span>;
    },
  },
  {
    accessorKey: "tokens_output",
    header: "Out Tokens",
    cell: ({ row }) => {
      const t = row.getValue("tokens_output") as number | null;
      return <span className="text-xs">{t ?? "—"}</span>;
    },
  },
  {
    accessorKey: "error_message",
    header: "Error",
    cell: ({ row }) => {
      const err = row.getValue("error_message") as string | null;
      return err ? (
        <span className="max-w-[200px] truncate text-xs text-red-500">{err}</span>
      ) : null;
    },
  },
];

export default function LLMCallsPage() {
  const [agentFilter, setAgentFilter] = useState("");
  const { data, isLoading } = useLLMCalls({
    agent_id: agentFilter || undefined,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">LLM Call Inspector</h1>
        <p className="text-muted-foreground">
          Monitor outbound LLM and A2A calls across the platform
        </p>
      </div>

      <div className="flex gap-3">
        <Input
          placeholder="Filter by agent ID..."
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
          className="max-w-xs"
        />
      </div>

      {isLoading ? (
        <div className="flex min-h-[200px] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <DataTable columns={columns} data={data?.calls ?? []} />
      )}
    </div>
  );
}
