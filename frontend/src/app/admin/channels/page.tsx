// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Send,
  Hash,
  Gamepad2,
  Users,
  MessageCircle,
  MessageSquare,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { DataTable, type ColumnDef } from "@/components/shared/data-table";
import { useAdminChannels } from "@/lib/hooks/use-channels";
import { formatCredits } from "@/lib/utils";
import type { AdminChannel, ChannelPlatform, ChannelStatus } from "@/types/channel";

const PLATFORM_ICONS: Record<ChannelPlatform, React.ReactNode> = {
  telegram: <Send className="h-4 w-4" />,
  slack: <Hash className="h-4 w-4" />,
  discord: <Gamepad2 className="h-4 w-4" />,
  teams: <Users className="h-4 w-4" />,
  whatsapp: <MessageCircle className="h-4 w-4" />,
};

const PLATFORM_LABELS: Record<ChannelPlatform, string> = {
  telegram: "Telegram",
  slack: "Slack",
  discord: "Discord",
  teams: "Microsoft Teams",
  whatsapp: "WhatsApp",
};

const STATUS_BADGE: Record<ChannelStatus, { label: string; className: string }> = {
  active: { label: "Active", className: "bg-green-500/15 text-green-400 border-green-500/30" },
  paused: { label: "Paused", className: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
  disconnected: { label: "Disconnected", className: "bg-red-500/15 text-red-400 border-red-500/30" },
  pending: { label: "Pending", className: "bg-gray-500/15 text-gray-400 border-gray-500/30" },
};

const columns: ColumnDef<AdminChannel, unknown>[] = [
  {
    accessorKey: "platform",
    header: "Platform",
    cell: ({ row }) => {
      const platform = row.original.platform;
      return (
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">{PLATFORM_ICONS[platform]}</span>
          <span className="text-sm">{PLATFORM_LABELS[platform]}</span>
        </div>
      );
    },
  },
  {
    accessorKey: "bot_name",
    header: "Bot Name",
    cell: ({ row }) => (
      <Link
        href={`/admin/channels/${row.original.id}`}
        className="font-medium hover:underline"
      >
        {row.original.bot_name}
      </Link>
    ),
  },
  {
    accessorKey: "owner_email",
    header: "Developer",
    cell: ({ row }) => (
      <div className="text-sm">
        <p className="font-medium">{row.original.owner_name}</p>
        <p className="text-muted-foreground">{row.original.owner_email}</p>
      </div>
    ),
  },
  {
    accessorKey: "agent_id",
    header: "Agent",
    cell: ({ row }) => (
      <span className="font-mono text-xs text-muted-foreground">
        {row.original.agent_id.slice(0, 8)}…
      </span>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => {
      const info = STATUS_BADGE[row.original.status];
      return (
        <Badge variant="outline" className={info.className}>
          {info.label}
        </Badge>
      );
    },
  },
  {
    accessorKey: "messages_today",
    header: "Messages Today",
    cell: ({ row }) => (
      <div className="flex items-center gap-1 text-sm text-muted-foreground">
        <MessageSquare className="h-3.5 w-3.5" />
        <span>{row.original.messages_today}</span>
      </div>
    ),
  },
  {
    accessorKey: "credits_used_today",
    header: "Credits Today",
    cell: ({ row }) => (
      <div className="flex items-center gap-1 text-sm text-muted-foreground">
        <Zap className="h-3.5 w-3.5" />
        <span>{formatCredits(row.original.credits_used_today)}</span>
      </div>
    ),
  },
];

export default function AdminChannelsPage() {
  const { data, isLoading } = useAdminChannels();
  const [search, setSearch] = useState("");

  const allChannels = data?.channels ?? [];
  const filtered = search
    ? allChannels.filter(
        (ch) =>
          ch.bot_name.toLowerCase().includes(search.toLowerCase()) ||
          ch.owner_email.toLowerCase().includes(search.toLowerCase())
      )
    : allChannels;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Channel Management</h1>
        <p className="mt-1 text-muted-foreground">
          {data ? `${data.total} total channels across all developers` : "All channels across all developers"}
        </p>
      </div>

      <div className="flex items-center gap-3">
        <Input
          placeholder="Search by bot name or developer email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
      </div>

      {isLoading ? (
        <p className="py-12 text-center text-sm text-muted-foreground">Loading channels…</p>
      ) : (
        <DataTable
          columns={columns}
          data={filtered}
          searchKey="bot_name"
          searchPlaceholder="Filter by bot name…"
        />
      )}
    </div>
  );
}
