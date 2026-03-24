// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { Send, Hash, Gamepad2, Users, MessageCircle, Zap, MessageSquare } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatRelativeTime, formatCredits } from "@/lib/utils";
import type { Channel, ChannelPlatform, ChannelStatus } from "@/types/channel";

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

interface ChannelCardProps {
  channel: Channel;
  actions?: React.ReactNode;
}

export function ChannelCard({ channel, actions }: ChannelCardProps) {
  const statusInfo = STATUS_BADGE[channel.status];
  const agentDisplay = channel.agent_name
    ? channel.agent_name
    : channel.agent_id.length > 12
      ? channel.agent_id.slice(0, 8) + "..."
      : channel.agent_id;

  return (
    <Card className="transition-all duration-200 hover:border-primary/50 hover:shadow-md">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              {PLATFORM_ICONS[channel.platform]}
            </div>
            <div className="min-w-0">
              <p className="font-semibold truncate">{channel.bot_name}</p>
              <p className="text-sm text-muted-foreground">{PLATFORM_LABELS[channel.platform]}</p>
            </div>
          </div>
          <Badge variant="outline" className={statusInfo.className}>
            {statusInfo.label}
          </Badge>
        </div>

        <div className="mt-3 space-y-0.5">
          <p className="text-xs text-muted-foreground">
            Agent: <span className={channel.agent_name ? "text-foreground" : "font-mono"}>{agentDisplay}</span>
          </p>
          {channel.workflow_name && (
            <p className="text-xs text-muted-foreground">
              Workflow: <span className="text-foreground">{channel.workflow_name}</span>
            </p>
          )}
        </div>

        <div className="mt-3 flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1 text-muted-foreground">
            <MessageSquare className="h-3.5 w-3.5" />
            <span>{channel.messages_today} today</span>
          </div>
          <div className="flex items-center gap-1 text-muted-foreground">
            <Zap className="h-3.5 w-3.5" />
            <span>{formatCredits(channel.credits_used_today)} credits</span>
          </div>
        </div>

        {(channel.total_messages !== undefined || channel.total_credits !== undefined) && (
          <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
            <span>{channel.total_messages ?? 0} total</span>
            <span>{channel.total_credits ?? "0"} credits total</span>
          </div>
        )}

        {channel.last_active_at && (
          <p className="mt-2 text-xs text-muted-foreground">
            Last active {formatRelativeTime(channel.last_active_at)}
          </p>
        )}

        {actions && (
          <div className="mt-4 flex items-center gap-2 border-t pt-3">
            {actions}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
