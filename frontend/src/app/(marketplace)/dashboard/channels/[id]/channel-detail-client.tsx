// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Send,
  Hash,
  Gamepad2,
  Users,
  MessageCircle,
  Pause,
  Play,
  RotateCcw,
  Trash2,
  Loader2,
  MessageSquare,
  Contact,
  BarChart2,
  Settings,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  useChannel,
  useUpdateChannel,
  useDeleteChannel,
  useRotateChannelToken,
} from "@/lib/hooks/use-channels";
import { ContactTable } from "@/components/channels/contact-table";
import { MessageLog } from "@/components/channels/message-log";
import { AnalyticsCharts } from "@/components/channels/analytics-charts";
import { formatCredits, formatRelativeTime } from "@/lib/utils";
import type { ChannelPlatform, ChannelStatus } from "@/types/channel";

const PLATFORM_ICONS: Record<ChannelPlatform, React.ComponentType<{ className?: string }>> = {
  telegram: Send,
  slack: Hash,
  discord: Gamepad2,
  teams: Users,
  whatsapp: MessageCircle,
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

interface ChannelDetailClientProps {
  channelId: string;
}

export default function ChannelDetailClient({ channelId }: ChannelDetailClientProps) {
  const router = useRouter();
  const { data: channel, isLoading } = useChannel(channelId);
  const updateChannel = useUpdateChannel();
  const deleteChannel = useDeleteChannel();
  const rotateToken = useRotateChannelToken();

  // Settings form state (synced when channel loads)
  const [dailyLimit, setDailyLimit] = useState<number>(0);
  const [lowBalance, setLowBalance] = useState<number>(20);
  const [pauseOnLimit, setPauseOnLimit] = useState<boolean>(true);
  const [settingsInitialized, setSettingsInitialized] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [togglingPause, setTogglingPause] = useState(false);

  // Initialize settings form once channel data arrives
  if (channel && !settingsInitialized) {
    setDailyLimit(channel.daily_credit_limit ?? 0);
    setLowBalance(channel.low_balance_threshold ?? 20);
    setPauseOnLimit(channel.pause_on_limit ?? true);
    setSettingsInitialized(true);
  }

  async function handleSaveSettings() {
    if (!channel) return;
    setSavingSettings(true);
    try {
      await updateChannel.mutateAsync({
        id: channel.id,
        data: {
          daily_credit_limit: dailyLimit || undefined,
          low_balance_threshold: lowBalance,
          pause_on_limit: pauseOnLimit,
        },
      });
      toast.success("Settings saved");
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setSavingSettings(false);
    }
  }

  async function handleTogglePause() {
    if (!channel) return;
    const newStatus = channel.status === "paused" ? "active" : "paused";
    setTogglingPause(true);
    try {
      await updateChannel.mutateAsync({ id: channel.id, data: { status: newStatus } });
      toast.success(`Channel ${newStatus === "paused" ? "paused" : "resumed"}`);
    } catch {
      toast.error("Failed to update channel status");
    } finally {
      setTogglingPause(false);
    }
  }

  async function handleRotateToken() {
    if (!channel) return;
    try {
      await rotateToken.mutateAsync({ channelId: channel.id, credentials: {} });
      toast.success("Token rotated successfully");
    } catch {
      toast.error("Failed to rotate token");
    }
  }

  async function handleDelete() {
    if (!channel) return;
    try {
      await deleteChannel.mutateAsync(channel.id);
      toast.success("Channel deleted");
      router.push("/dashboard/channels");
    } catch {
      toast.error("Failed to delete channel");
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading channel...
      </div>
    );
  }

  if (!channel) {
    return (
      <div className="py-20 text-center">
        <p className="text-muted-foreground">Channel not found</p>
        <Button variant="link" asChild className="mt-2">
          <Link href="/dashboard/channels">Back to Channels</Link>
        </Button>
      </div>
    );
  }

  const PlatformIcon = PLATFORM_ICONS[channel.platform];
  const statusInfo = STATUS_BADGE[channel.status];
  const canToggle = channel.status === "active" || channel.status === "paused";

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        href="/dashboard/channels"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to Channels
      </Link>

      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <PlatformIcon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <h1 className="text-xl font-bold leading-none">{channel.bot_name}</h1>
          <p className="text-sm text-muted-foreground">{PLATFORM_LABELS[channel.platform]}</p>
        </div>
        <Badge variant="outline" className={statusInfo.className}>
          {statusInfo.label}
        </Badge>
      </div>

      {/* 5-Tab layout */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="contacts" className="gap-1.5">
            <Contact className="h-3.5 w-3.5" />
            Contacts
          </TabsTrigger>
          <TabsTrigger value="messages" className="gap-1.5">
            <MessageSquare className="h-3.5 w-3.5" />
            Messages
          </TabsTrigger>
          <TabsTrigger value="analytics" className="gap-1.5">
            <BarChart2 className="h-3.5 w-3.5" />
            Analytics
          </TabsTrigger>
          <TabsTrigger value="settings" className="gap-1.5">
            <Settings className="h-3.5 w-3.5" />
            Settings
          </TabsTrigger>
        </TabsList>

        {/* ── Overview Tab ── */}
        <TabsContent value="overview" className="mt-6 space-y-6">
          {/* 4 stat cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Messages Today</p>
                <p className="mt-1 text-2xl font-bold">{channel.messages_today}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Active Contacts</p>
                <p className="mt-1 text-2xl font-bold">—</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Credits Used</p>
                <p className="mt-1 text-2xl font-bold">
                  {formatCredits(channel.credits_used_today)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Avg Response Time</p>
                <p className="mt-1 text-2xl font-bold">—</p>
              </CardContent>
            </Card>
          </div>

          {/* Recent messages (compact) */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Recent Messages</CardTitle>
            </CardHeader>
            <CardContent>
              <MessageLog channelId={channelId} />
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Contacts Tab ── */}
        <TabsContent value="contacts" className="mt-6">
          <ContactTable channelId={channelId} />
        </TabsContent>

        {/* ── Messages Tab ── */}
        <TabsContent value="messages" className="mt-6">
          <MessageLog channelId={channelId} />
        </TabsContent>

        {/* ── Analytics Tab ── */}
        <TabsContent value="analytics" className="mt-6">
          <AnalyticsCharts channelId={channelId} />
        </TabsContent>

        {/* ── Settings Tab ── */}
        <TabsContent value="settings" className="mt-6 space-y-6">
          {/* Channel info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Channel Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Platform</span>
                <span className="font-medium capitalize">{PLATFORM_LABELS[channel.platform]}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Agent ID</span>
                <span className="font-mono text-xs">{channel.agent_id}</span>
              </div>
              {channel.webhook_url && (
                <div className="flex flex-col gap-1">
                  <span className="text-muted-foreground">Webhook URL</span>
                  <code className="rounded bg-muted/50 px-2 py-1 text-xs break-all">
                    {channel.webhook_url}
                  </code>
                </div>
              )}
              {channel.last_active_at && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Last Active</span>
                  <span>{formatRelativeTime(channel.last_active_at)}</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Budget controls */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Budget Controls</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="daily-limit">Daily Credit Limit</Label>
                <Input
                  id="daily-limit"
                  type="number"
                  min={0}
                  value={dailyLimit}
                  onChange={(e) => setDailyLimit(Number(e.target.value))}
                />
                <p className="text-xs text-muted-foreground">Max credits per day (0 = unlimited)</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="low-balance">Low Balance Alert</Label>
                <Input
                  id="low-balance"
                  type="number"
                  min={0}
                  value={lowBalance}
                  onChange={(e) => setLowBalance(Number(e.target.value))}
                />
                <p className="text-xs text-muted-foreground">
                  Notify when account credits drop below this
                </p>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="pause-on-limit">Auto-Pause on Limit</Label>
                  <p className="text-xs text-muted-foreground">
                    Pause channel when daily limit is reached
                  </p>
                </div>
                <Switch
                  id="pause-on-limit"
                  checked={pauseOnLimit}
                  onCheckedChange={setPauseOnLimit}
                />
              </div>
              <Button
                onClick={handleSaveSettings}
                disabled={savingSettings}
                className="w-full"
              >
                {savingSettings ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                Save Settings
              </Button>
            </CardContent>
          </Card>

          {/* Token rotation */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Token Rotation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Rotate the channel&apos;s authentication token. This will disconnect the
                channel until the new token is verified.
              </p>
              <Button
                variant="outline"
                onClick={handleRotateToken}
                disabled={rotateToken.isPending}
              >
                {rotateToken.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RotateCcw className="mr-2 h-4 w-4" />
                )}
                Rotate Token
              </Button>
            </CardContent>
          </Card>

          {/* Pause / Resume */}
          {canToggle && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Channel Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  {channel.status === "paused"
                    ? "This channel is currently paused. Resume to accept new messages."
                    : "Pause this channel to temporarily stop accepting messages."}
                </p>
                <Button
                  variant="outline"
                  onClick={handleTogglePause}
                  disabled={togglingPause}
                >
                  {togglingPause ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : channel.status === "paused" ? (
                    <Play className="mr-2 h-4 w-4" />
                  ) : (
                    <Pause className="mr-2 h-4 w-4" />
                  )}
                  {channel.status === "paused" ? "Resume Channel" : "Pause Channel"}
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Danger zone */}
          <Card className="border-destructive/30">
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-destructive">
                Danger Zone
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Permanently delete this channel. This will disconnect the bot from{" "}
                {PLATFORM_LABELS[channel.platform]} and cannot be undone.
              </p>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive" size="sm">
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete Channel
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete channel?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will permanently delete{" "}
                      <strong>{channel.bot_name}</strong> and disconnect it from{" "}
                      {PLATFORM_LABELS[channel.platform]}. All message history will be
                      lost. This action cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      onClick={handleDelete}
                      disabled={deleteChannel.isPending}
                    >
                      {deleteChannel.isPending ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : null}
                      Delete permanently
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
