// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import {
  Send,
  Hash,
  Gamepad2,
  Users,
  MessageCircle,
  Plus,
  Pause,
  Play,
  Trash2,
  Loader2,
  MessageSquare,
  Coins,
  Radio,
  Copy,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useChannels, useUpdateChannel, useDeleteChannel } from "@/lib/hooks/use-channels";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { ChannelWizard } from "./channel-wizard";
import type { Channel, ChannelStatus } from "@/types/channel";

const PLATFORM_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  telegram: Send,
  slack: Hash,
  discord: Gamepad2,
  teams: Users,
  whatsapp: MessageCircle,
};

const STATUS_STYLES: Record<ChannelStatus, { dot: string; label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  active: { dot: "bg-green-500", label: "Active", variant: "outline" },
  paused: { dot: "bg-yellow-500", label: "Paused", variant: "secondary" },
  disconnected: { dot: "bg-red-500", label: "Disconnected", variant: "destructive" },
  pending: { dot: "bg-gray-400", label: "Pending", variant: "secondary" },
};

function relativeTime(dateStr?: string): string {
  if (!dateStr) return "Never";
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function ChannelsTab() {
  const { data, isLoading } = useChannels();
  const updateChannel = useUpdateChannel();
  const deleteChannel = useDeleteChannel();
  const [wizardOpen, setWizardOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Channel | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const channels = data?.channels ?? [];

  async function handleTogglePause(channel: Channel) {
    setTogglingId(channel.id);
    const newStatus = channel.status === "paused" ? "active" : "paused";
    try {
      await updateChannel.mutateAsync({
        id: channel.id,
        data: { status: newStatus },
      });
      toast.success(`Channel ${newStatus === "paused" ? "paused" : "resumed"}`);
    } catch {
      toast.error("Failed to update channel status");
    } finally {
      setTogglingId(null);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteChannel.mutateAsync(deleteTarget.id);
      toast.success("Channel deleted");
      setDeleteTarget(null);
    } catch {
      toast.error("Failed to delete channel");
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-12 justify-center text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading channels...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">Connected Channels</h2>
          <p className="text-xs text-muted-foreground">
            Deploy your agents to messaging platforms
          </p>
        </div>
        <Button onClick={() => setWizardOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Connect Channel
        </Button>
      </div>

      {/* Empty state */}
      {channels.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12">
            <Radio className="h-10 w-10 text-muted-foreground/40" />
            <div className="text-center">
              <p className="text-sm font-medium">No channels connected</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Connect Telegram, Slack, Discord, Teams, or WhatsApp to let users
                interact with your agents from their favorite platforms.
              </p>
            </div>
            <Button variant="outline" onClick={() => setWizardOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Connect a Channel
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Channel cards */}
      {channels.map((channel) => {
        const Icon = PLATFORM_ICONS[channel.platform] ?? MessageCircle;
        const status = STATUS_STYLES[channel.status] ?? STATUS_STYLES.pending;
        const isToggling = togglingId === channel.id;

        return (
          <Card key={channel.id}>
            <CardContent className="flex items-center gap-4 p-4">
              {/* Platform icon */}
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border bg-muted/50">
                <Icon className="h-5 w-5" />
              </div>

              {/* Info */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium truncate">
                    {channel.bot_name}
                  </span>
                  <Badge variant={status.variant} className="gap-1 text-[10px]">
                    <span className={`inline-block h-1.5 w-1.5 rounded-full ${status.dot}`} />
                    {status.label}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground truncate capitalize">
                  {channel.platform} &middot; Last active: {relativeTime(channel.last_active_at)}
                </p>
                {channel.error_message && (
                  <p className="mt-0.5 text-xs text-destructive truncate">
                    {channel.error_message}
                  </p>
                )}
                {channel.status === "pending" && channel.webhook_url && (
                  <div className="mt-2 rounded-md bg-amber-500/10 border border-amber-500/20 p-2">
                    <p className="text-xs font-medium text-amber-500">Webhook not configured</p>
                    <div className="flex items-center gap-2 mt-1">
                      <code className="text-xs bg-background px-2 py-0.5 rounded flex-1 truncate">{channel.webhook_url}</code>
                      <Button size="sm" variant="ghost" onClick={() => { navigator.clipboard.writeText(channel.webhook_url!); toast.success("Webhook URL copied"); }}>
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              {/* Stats */}
              <div className="hidden sm:flex items-center gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1" title="Messages today">
                  <MessageSquare className="h-3.5 w-3.5" />
                  {channel.messages_today}
                </span>
                <span className="flex items-center gap-1" title="Credits used today">
                  <Coins className="h-3.5 w-3.5" />
                  {channel.credits_used_today}
                </span>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1">
                {(channel.status === "active" || channel.status === "paused") && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handleTogglePause(channel)}
                    disabled={isToggling}
                    title={channel.status === "paused" ? "Resume" : "Pause"}
                  >
                    {isToggling ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : channel.status === "paused" ? (
                      <Play className="h-3.5 w-3.5" />
                    ) : (
                      <Pause className="h-3.5 w-3.5" />
                    )}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive hover:text-destructive"
                  onClick={() => setDeleteTarget(channel)}
                  title="Delete"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}

      {/* Wizard dialog */}
      <ChannelWizard open={wizardOpen} onOpenChange={setWizardOpen} existingChannelCount={channels.length} />

      {/* Delete confirmation */}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}
        title="Delete Channel"
        description={`Are you sure you want to delete the ${deleteTarget?.bot_name ?? ""} channel? This will disconnect it from ${deleteTarget?.platform ?? "the platform"} and cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        loading={deleteChannel.isPending}
      />
    </div>
  );
}
