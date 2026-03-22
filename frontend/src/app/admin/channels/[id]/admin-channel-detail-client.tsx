// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  Send,
  Hash,
  Gamepad2,
  Users,
  MessageCircle,
  ArrowLeft,
  PauseCircle,
  Unplug,
  AlertTriangle,
  Info,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { ContactTable } from "@/components/channels/contact-table";
import { AnalyticsCharts } from "@/components/channels/analytics-charts";
import { AdminAccessGate } from "@/components/channels/admin-access-gate";
import { MessageLog } from "@/components/channels/message-log";
import { useAdminChannel } from "@/lib/hooks/use-channels";
import { useAuth } from "@/lib/auth-context";
import { useUpdateChannel } from "@/lib/hooks/use-channels";
import { formatCredits } from "@/lib/utils";
import type { ChannelPlatform, ChannelStatus } from "@/types/channel";

const PLATFORM_ICONS: Record<ChannelPlatform, React.ReactNode> = {
  telegram: <Send className="h-5 w-5" />,
  slack: <Hash className="h-5 w-5" />,
  discord: <Gamepad2 className="h-5 w-5" />,
  teams: <Users className="h-5 w-5" />,
  whatsapp: <MessageCircle className="h-5 w-5" />,
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

interface AdminChannelDetailClientProps {
  channelId: string;
}

export default function AdminChannelDetailClient({ channelId }: AdminChannelDetailClientProps) {
  const { data: channel, isLoading } = useAdminChannel(channelId);
  const { user } = useAuth();
  const updateChannel = useUpdateChannel();

  // Messages tab justification state
  const [activeTab, setActiveTab] = useState("overview");
  const [justification, setJustification] = useState<string | null>(null);
  const [showGate, setShowGate] = useState(false);

  function handleMessagesTabClick() {
    if (!justification) {
      setShowGate(true);
    }
    setActiveTab("messages");
  }

  function handleJustificationConfirm(reason: string) {
    setJustification(reason);
    setShowGate(false);
  }

  function handleJustificationCancel() {
    setShowGate(false);
    // Revert tab to overview if not yet justified
    if (!justification) {
      setActiveTab("overview");
    }
  }

  function handleForcePause() {
    updateChannel.mutate(
      { id: channelId, data: { status: "paused" } },
      {
        onSuccess: () => toast.success("Channel paused"),
        onError: () => toast.error("Failed to pause channel"),
      }
    );
  }

  function handleForceDisconnect() {
    updateChannel.mutate(
      { id: channelId, data: { status: "paused" } },
      {
        onSuccess: () => toast.success("Channel disconnected"),
        onError: () => toast.error("Failed to disconnect channel"),
      }
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading channel…</p>
      </div>
    );
  }

  if (!channel) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3">
        <p className="text-sm text-muted-foreground">Channel not found.</p>
        <Link href="/admin/channels" className="text-sm text-primary hover:underline">
          ← Back to Channels
        </Link>
      </div>
    );
  }

  const statusInfo = STATUS_BADGE[channel.status];
  const tierLabel: Record<string, string> = {
    free: "Free",
    starter: "Starter",
    pro: "Pro",
    enterprise: "Enterprise",
  };

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        href="/admin/channels"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to Channels
      </Link>

      {/* Developer info card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-muted-foreground">Developer</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-3">
          <div>
            <p className="text-xs text-muted-foreground">Name</p>
            <p className="font-medium">{channel.owner_name}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Email</p>
            <p className="font-medium">{channel.owner_email}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Credit Balance</p>
            <p className="font-medium">{formatCredits(channel.owner_credit_balance)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Account Tier</p>
            <Badge variant="outline" className="text-xs">
              {tierLabel[channel.owner_account_tier] ?? channel.owner_account_tier}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Channel header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            {PLATFORM_ICONS[channel.platform]}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold">{channel.bot_name}</h1>
              <Badge variant="outline" className={statusInfo.className}>
                {statusInfo.label}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{PLATFORM_LABELS[channel.platform]}</p>
          </div>
        </div>

        {/* Admin actions */}
        <div className="flex items-center gap-2">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                disabled={channel.status === "paused" || updateChannel.isPending}
              >
                <PauseCircle className="h-4 w-4 mr-1.5" />
                Force Pause
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Force-pause this channel?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will immediately pause the channel. The developer will be notified and can
                  resume it from their dashboard.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleForcePause}>Pause Channel</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="destructive"
                size="sm"
                disabled={channel.status === "disconnected" || updateChannel.isPending}
              >
                <Unplug className="h-4 w-4 mr-1.5" />
                Force Disconnect
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-destructive" />
                  Force-disconnect this channel?
                </AlertDialogTitle>
                <AlertDialogDescription>
                  This will disconnect the channel and stop all message processing. The developer
                  will need to reconnect the bot to resume service.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  onClick={handleForceDisconnect}
                >
                  Disconnect
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(val) => {
        if (val === "messages") {
          handleMessagesTabClick();
        } else {
          setActiveTab(val);
        }
      }}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="contacts">Contacts</TabsTrigger>
          <TabsTrigger value="messages">Messages</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        {/* Overview */}
        <TabsContent value="overview" className="mt-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="pt-5">
                <p className="text-xs text-muted-foreground">Messages Today</p>
                <p className="mt-1 text-2xl font-bold">{channel.messages_today}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5">
                <p className="text-xs text-muted-foreground">Credits Used Today</p>
                <p className="mt-1 text-2xl font-bold">{formatCredits(channel.credits_used_today)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5">
                <p className="text-xs text-muted-foreground">Daily Credit Limit</p>
                <p className="mt-1 text-2xl font-bold">
                  {channel.daily_credit_limit ? formatCredits(channel.daily_credit_limit) : "—"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5">
                <p className="text-xs text-muted-foreground">Agent ID</p>
                <p className="mt-1 font-mono text-sm truncate">{channel.agent_id}</p>
              </CardContent>
            </Card>
          </div>
          {channel.error_message && (
            <Card className="mt-4 border-destructive/40 bg-destructive/5">
              <CardContent className="flex items-start gap-2 pt-4">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                <p className="text-sm text-destructive">{channel.error_message}</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Contacts */}
        <TabsContent value="contacts" className="mt-4">
          <ContactTable channelId={channelId} />
        </TabsContent>

        {/* Messages — justification-gated */}
        <TabsContent value="messages" className="mt-4">
          {showGate && (
            <AdminAccessGate
              onConfirm={handleJustificationConfirm}
              onCancel={handleJustificationCancel}
            />
          )}
          {justification ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-4 py-2.5 text-sm text-amber-400">
                <Info className="h-4 w-4 shrink-0" />
                <span>
                  Access logged: <strong>{justification}</strong>
                  {user?.email ? ` — ${user.email}` : ""}
                </span>
              </div>
              <MessageLog channelId={channelId} />
            </div>
          ) : !showGate ? (
            <div className="flex flex-col items-center justify-center gap-3 py-16">
              <p className="text-sm text-muted-foreground">
                Access to messages requires justification.
              </p>
              <Button variant="outline" size="sm" onClick={() => setShowGate(true)}>
                Provide Justification
              </Button>
            </div>
          ) : null}
        </TabsContent>

        {/* Analytics */}
        <TabsContent value="analytics" className="mt-4">
          <AnalyticsCharts channelId={channelId} />
        </TabsContent>

        {/* Settings */}
        <TabsContent value="settings" className="mt-4">
          <Card>
            <CardContent className="pt-5 space-y-3 text-sm">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs text-muted-foreground">Webhook URL</p>
                  <p className="font-mono text-xs break-all">{channel.webhook_url ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Pause on Limit</p>
                  <p>{channel.pause_on_limit ? "Enabled" : "Disabled"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Low Balance Threshold</p>
                  <p>{formatCredits(channel.low_balance_threshold)}</p>
                </div>
                {channel.paused_reason && (
                  <div>
                    <p className="text-xs text-muted-foreground">Paused Reason</p>
                    <p>{channel.paused_reason}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
