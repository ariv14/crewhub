// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Radio,
  Pause,
  Play,
  Settings2,
  Loader2,
  Plus,
  MessageSquare,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { toast } from "sonner";
import { useChannels, useUpdateChannel } from "@/lib/hooks/use-channels";
import { ChannelCard } from "@/components/channels/channel-card";
import { ChannelWizard } from "../settings/channel-wizard";
import { formatCredits } from "@/lib/utils";
import type { Channel } from "@/types/channel";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}

export default function ChannelsPage() {
  const { data, isLoading } = useChannels();
  const updateChannel = useUpdateChannel();
  const [wizardOpen, setWizardOpen] = useState(false);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const channels = data?.channels ?? [];

  const totalMessages = channels.reduce((sum, c) => sum + c.messages_today, 0);
  const totalCredits = channels.reduce((sum, c) => sum + c.credits_used_today, 0);

  async function handleTogglePause(channel: Channel) {
    setTogglingId(channel.id);
    const newStatus = channel.status === "paused" ? "active" : "paused";
    try {
      await updateChannel.mutateAsync({ id: channel.id, data: { status: newStatus } });
      toast.success(`Channel ${newStatus === "paused" ? "paused" : "resumed"}`);
    } catch {
      toast.error("Failed to update channel status");
    } finally {
      setTogglingId(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">Channels</h1>
        <p className="mt-1 text-muted-foreground">
          Manage your messaging platform connections
        </p>
      </div>

      {/* Stats strip */}
      {!isLoading && channels.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <StatCard label="Total Channels" value={channels.length} />
          <StatCard
            label="Messages Today"
            value={totalMessages.toLocaleString()}
          />
          <StatCard label="Credits Today" value={formatCredits(totalCredits)} />
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading channels...
        </div>
      )}

      {/* Empty state */}
      {!isLoading && channels.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-16">
            <Radio className="h-12 w-12 text-muted-foreground/30" />
            <div className="text-center">
              <p className="text-base font-semibold">No channels connected</p>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                Connect Telegram, Slack, Discord, Microsoft Teams, or WhatsApp
                to let users interact with your agents from their favorite
                platforms.
              </p>
            </div>
            <Button onClick={() => setWizardOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Connect a Channel
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Channel grid */}
      {!isLoading && channels.length > 0 && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {channels.length} channel{channels.length !== 1 ? "s" : ""}{" "}
              connected
            </p>
            <Button onClick={() => setWizardOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Connect a Channel
            </Button>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {channels.map((channel) => {
              const isToggling = togglingId === channel.id;
              const canToggle =
                channel.status === "active" || channel.status === "paused";

              return (
                <ChannelCard
                  key={channel.id}
                  channel={channel}
                  actions={
                    <>
                      {canToggle && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1.5"
                          onClick={() => handleTogglePause(channel)}
                          disabled={isToggling}
                        >
                          {isToggling ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : channel.status === "paused" ? (
                            <Play className="h-3.5 w-3.5" />
                          ) : (
                            <Pause className="h-3.5 w-3.5" />
                          )}
                          {channel.status === "paused" ? "Resume" : "Pause"}
                        </Button>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-1.5"
                        asChild
                      >
                        <Link href={`/dashboard/channels/${channel.id}`}>
                          <Settings2 className="h-3.5 w-3.5" />
                          Configure
                        </Link>
                      </Button>
                    </>
                  }
                />
              );
            })}
          </div>
        </>
      )}

      <ChannelWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        existingChannelCount={channels.length}
      />
    </div>
  );
}
