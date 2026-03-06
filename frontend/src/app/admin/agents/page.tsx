"use client";

import { useAgents } from "@/lib/hooks/use-agents";
import { AGENT_STATUS_COLORS, VERIFICATION_COLORS, ROUTES } from "@/lib/constants";
import { cn, formatRelativeTime } from "@/lib/utils";
import { DataTable, SortableHeader, type ColumnDef } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import type { Agent } from "@/types/agent";

const columns: ColumnDef<Agent, unknown>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => <SortableHeader column={column}>Name</SortableHeader>,
    cell: ({ row }) => (
      <a
        href={ROUTES.adminAgentDetail(row.original.id)}
        className="font-medium hover:text-primary hover:underline"
      >
        {row.original.name}
      </a>
    ),
  },
  {
    accessorKey: "category",
    header: "Category",
    cell: ({ row }) => (
      <Badge variant="secondary" className="text-xs">
        {row.original.category}
      </Badge>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge
        variant="outline"
        className={cn("text-xs capitalize", AGENT_STATUS_COLORS[row.original.status])}
      >
        {row.original.status}
      </Badge>
    ),
  },
  {
    accessorKey: "verification_level",
    header: "Verification",
    cell: ({ row }) => (
      <Badge
        variant="outline"
        className={cn("text-xs capitalize", VERIFICATION_COLORS[row.original.verification_level])}
      >
        {row.original.verification_level}
      </Badge>
    ),
  },
  {
    accessorKey: "reputation_score",
    header: ({ column }) => (
      <SortableHeader column={column}>Reputation</SortableHeader>
    ),
    cell: ({ row }) => row.original.reputation_score.toFixed(1),
  },
  {
    accessorKey: "total_tasks_completed",
    header: ({ column }) => (
      <SortableHeader column={column}>Tasks</SortableHeader>
    ),
  },
  {
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {formatRelativeTime(row.original.created_at)}
      </span>
    ),
  },
];

export default function AdminAgentsPage() {
  const { data, isLoading } = useAgents({ per_page: 100 });
  const agents = data?.agents ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">All Agents</h1>
        <p className="mt-1 text-muted-foreground">
          Manage all registered agents on the platform
        </p>
      </div>

      <DataTable
        columns={columns}
        data={agents}
        searchKey="name"
        searchPlaceholder="Search agents..."
      />
    </div>
  );
}
