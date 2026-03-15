// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useAdminUsers, useUpdateUserStatus } from "@/lib/hooks/use-admin";
import { formatRelativeTime } from "@/lib/utils";
import { DataTable, SortableHeader, type ColumnDef } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { User } from "@/types/auth";

function UserActionsCell({ user }: { user: User }) {
  const mutation = useUpdateUserStatus();

  return (
    <div className="flex gap-2">
      <Button
        size="sm"
        variant={user.is_active ? "destructive" : "default"}
        onClick={() =>
          mutation.mutate({
            userId: user.id,
            data: { is_active: !user.is_active },
          })
        }
        disabled={mutation.isPending}
      >
        {user.is_active ? "Deactivate" : "Activate"}
      </Button>
      <Button
        size="sm"
        variant="outline"
        onClick={() =>
          mutation.mutate({
            userId: user.id,
            data: { is_admin: !user.is_admin },
          })
        }
        disabled={mutation.isPending}
      >
        {user.is_admin ? "Revoke Admin" : "Grant Admin"}
      </Button>
    </div>
  );
}

const columns: ColumnDef<User, unknown>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => (
      <span className="font-mono text-xs">{row.original.id.slice(0, 8)}...</span>
    ),
  },
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.name}</span>
    ),
  },
  {
    accessorKey: "email",
    header: "Email",
  },
  {
    accessorKey: "is_active",
    header: "Status",
    cell: ({ row }) => (
      <Badge variant={row.original.is_active ? "default" : "destructive"} className="text-xs">
        {row.original.is_active ? "Active" : "Inactive"}
      </Badge>
    ),
  },
  {
    accessorKey: "is_admin",
    header: "Role",
    cell: ({ row }) => (
      <Badge variant={row.original.is_admin ? "secondary" : "outline"} className="text-xs">
        {row.original.is_admin ? "Admin" : "User"}
      </Badge>
    ),
  },
  {
    accessorKey: "created_at",
    header: ({ column }) => <SortableHeader column={column}>Joined</SortableHeader>,
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {formatRelativeTime(row.original.created_at)}
      </span>
    ),
  },
  {
    id: "actions",
    header: "Actions",
    cell: ({ row }) => <UserActionsCell user={row.original} />,
  },
];

export default function AdminUsersPage() {
  const { data } = useAdminUsers({ per_page: 100 });
  const users = data?.users ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">User Management</h1>
        <p className="mt-1 text-muted-foreground">
          {data ? `${data.total} total users` : "Manage platform users"}
        </p>
      </div>

      <DataTable
        columns={columns}
        data={users}
        searchKey="email"
        searchPlaceholder="Search by email..."
      />
    </div>
  );
}
