// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useAdminTransactions } from "@/lib/hooks/use-admin";
import { formatCredits, formatRelativeTime } from "@/lib/utils";
import { DataTable, SortableHeader, type ColumnDef } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import type { Transaction } from "@/types/credits";

const columns: ColumnDef<Transaction, unknown>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => (
      <span className="font-mono text-xs">{row.original.id.slice(0, 8)}...</span>
    ),
  },
  {
    accessorKey: "type",
    header: "Type",
    cell: ({ row }) => (
      <Badge variant="outline" className="text-xs capitalize">
        {row.original.type.replace(/_/g, " ")}
      </Badge>
    ),
  },
  {
    accessorKey: "amount",
    header: ({ column }) => <SortableHeader column={column}>Amount</SortableHeader>,
    cell: ({ row }) => (
      <span className="font-mono text-sm">{formatCredits(row.original.amount)}</span>
    ),
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {row.original.description}
      </span>
    ),
  },
  {
    accessorKey: "created_at",
    header: ({ column }) => <SortableHeader column={column}>Date</SortableHeader>,
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {formatRelativeTime(row.original.created_at)}
      </span>
    ),
  },
];

export default function AdminTransactionsPage() {
  const { data } = useAdminTransactions({ per_page: 100 });
  const transactions = data?.transactions ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Transaction Audit</h1>
        <p className="mt-1 text-muted-foreground">
          All platform transactions
          {data ? ` — ${data.total} total` : ""}
        </p>
      </div>

      <DataTable
        columns={columns}
        data={transactions}
        searchKey="description"
        searchPlaceholder="Search transactions..."
      />
    </div>
  );
}
