// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { MoreHorizontal, ExternalLink, Shield, Power } from "lucide-react";
import { toast } from "sonner";
import { useAgents } from "@/lib/hooks/use-agents";
import { useUpdateAgentStatus, useUpdateAgentVerification } from "@/lib/hooks/use-admin";
import { AGENT_STATUS_COLORS, VERIFICATION_COLORS, ROUTES } from "@/lib/constants";
import { cn, formatRelativeTime } from "@/lib/utils";
import { DataTable, SortableHeader, type ColumnDef } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Agent } from "@/types/agent";

function ActionsCell({ agent }: { agent: Agent }) {
  const statusMutation = useUpdateAgentStatus();
  const verificationMutation = useUpdateAgentVerification();

  const toggleStatus = () => {
    const newStatus = agent.status === "active" ? "inactive" : "active";
    statusMutation.mutate(
      { agentId: agent.id, status: newStatus },
      {
        onSuccess: () => toast.success(`Agent status changed to ${newStatus}`),
        onError: (err) => toast.error(err instanceof Error ? err.message : "Failed to update status"),
      }
    );
  };

  const setVerification = (level: string) => {
    verificationMutation.mutate(
      { agentId: agent.id, level },
      {
        onSuccess: () => toast.success(`Verification set to ${level}`),
        onError: (err) => toast.error(err instanceof Error ? err.message : "Failed to update verification"),
      }
    );
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <MoreHorizontal className="h-4 w-4" />
          <span className="sr-only">Actions</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={toggleStatus} disabled={statusMutation.isPending}>
          <Power className="mr-2 h-4 w-4" />
          {agent.status === "active" ? "Set Inactive" : "Set Active"}
        </DropdownMenuItem>

        <DropdownMenuSub>
          <DropdownMenuSubTrigger>
            <Shield className="mr-2 h-4 w-4" />
            Set Verification
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent>
            {(["new", "verified", "certified"] as const).map((level) => (
              <DropdownMenuItem
                key={level}
                onClick={() => setVerification(level)}
                disabled={verificationMutation.isPending || agent.verification_level === level}
                className="capitalize"
              >
                {level}
                {agent.verification_level === level && (
                  <span className="ml-2 text-muted-foreground">(current)</span>
                )}
              </DropdownMenuItem>
            ))}
          </DropdownMenuSubContent>
        </DropdownMenuSub>

        <DropdownMenuItem asChild>
          <a href={ROUTES.agentDetail(agent.id)}>
            <ExternalLink className="mr-2 h-4 w-4" />
            View Agent
          </a>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

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
  {
    id: "actions",
    header: "Actions",
    cell: ({ row }) => <ActionsCell agent={row.original} />,
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
