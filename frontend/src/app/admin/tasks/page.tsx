"use client";

import { useAdminTasks } from "@/lib/hooks/use-admin";
import { formatRelativeTime } from "@/lib/utils";
import { TaskStatusBadge } from "@/components/tasks/task-status-badge";
import { DataTable, SortableHeader, type ColumnDef } from "@/components/shared/data-table";
import type { Task } from "@/types/task";

const columns: ColumnDef<Task, unknown>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => (
      <span className="font-mono text-xs">{row.original.id.slice(0, 8)}...</span>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <TaskStatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "skill_id",
    header: "Skill",
    cell: ({ row }) => (
      <span className="text-sm">
        {String(row.original.skill_id).slice(0, 20)}
      </span>
    ),
  },
  {
    accessorKey: "payment_method",
    header: "Payment",
    cell: ({ row }) => (
      <span className="text-sm capitalize">{row.original.payment_method}</span>
    ),
  },
  {
    accessorKey: "credits_charged",
    header: ({ column }) => <SortableHeader column={column}>Credits</SortableHeader>,
    cell: ({ row }) => (
      <span className="text-sm">
        {row.original.credits_charged || row.original.credits_quoted}
      </span>
    ),
  },
  {
    accessorKey: "created_at",
    header: ({ column }) => <SortableHeader column={column}>Created</SortableHeader>,
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {formatRelativeTime(row.original.created_at)}
      </span>
    ),
  },
];

export default function AdminTasksPage() {
  const { data } = useAdminTasks({ per_page: 100 });
  const tasks = data?.tasks ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Task Monitor</h1>
        <p className="mt-1 text-muted-foreground">
          All platform tasks (auto-refreshes every 5s)
          {data ? ` — ${data.total} total` : ""}
        </p>
      </div>

      <DataTable
        columns={columns}
        data={tasks}
        searchKey="id"
        searchPlaceholder="Search tasks..."
      />
    </div>
  );
}
