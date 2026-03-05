"use client";

import { Bot, CheckCircle2, CreditCard, AlertTriangle, Rocket } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useActivityFeed, type ActivityEvent } from "@/lib/hooks/use-activity-feed";
import { cn } from "@/lib/utils";

const EVENT_CONFIG: Record<
  string,
  { icon: typeof Bot; label: string; color: string }
> = {
  task_created: { icon: Rocket, label: "Task created", color: "text-blue-500" },
  task_completed: { icon: CheckCircle2, label: "Task completed", color: "text-green-500" },
  task_failed: { icon: AlertTriangle, label: "Task failed", color: "text-red-500" },
  agent_registered: { icon: Bot, label: "Agent registered", color: "text-purple-500" },
  credit_transaction: { icon: CreditCard, label: "Transaction", color: "text-amber-500" },
};

function formatRelativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function getEventDescription(event: ActivityEvent): string {
  const agentName = event.agent_name as string | undefined;
  const msgPreview = event.message_preview as string | undefined;
  const name = event.name as string | undefined;
  const txType = event.tx_type as string | undefined;
  const amount = event.amount as string | undefined;

  switch (event.type) {
    case "task_created": {
      const parts: string[] = [];
      if (agentName) parts.push(agentName);
      if (msgPreview) parts.push(`"${msgPreview.slice(0, 60)}${msgPreview.length > 60 ? "..." : ""}"`);
      return parts.length ? parts.join(" — ") : "New task submitted";
    }
    case "task_completed": {
      if (agentName) return `${agentName} completed task`;
      return "Task completed";
    }
    case "task_failed": {
      if (agentName) return `${agentName} — task failed`;
      return "Task failed";
    }
    case "agent_registered":
      return name ?? "New agent";
    case "credit_transaction": {
      if (txType && amount) return `${txType}: ${amount} credits`;
      return txType ?? "Credit transaction";
    }
    default:
      return name ?? event.type;
  }
}

function EventRow({ event }: { event: ActivityEvent }) {
  const config = EVENT_CONFIG[event.type] ?? {
    icon: Bot,
    label: event.type,
    color: "text-muted-foreground",
  };
  const Icon = config.icon;
  const createdAt = event.created_at as string | undefined;
  const isRecent =
    createdAt && Date.now() - new Date(createdAt).getTime() < 30_000;

  return (
    <div className="flex items-start gap-3 py-2.5">
      <div className="relative mt-0.5 shrink-0">
        <Icon className={cn("h-4 w-4", config.color)} />
        {isRecent && (
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 animate-pulse rounded-full bg-green-400" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-muted-foreground">
          {config.label}
        </p>
        <p className="mt-0.5 truncate text-sm">
          {getEventDescription(event)}
        </p>
      </div>
      {createdAt && (
        <span className="shrink-0 text-xs text-muted-foreground">
          {formatRelativeTime(createdAt)}
        </span>
      )}
    </div>
  );
}

export function ActivityFeed() {
  const { events, connected } = useActivityFeed();

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Live Activity</CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              {connected ? "Live" : "Offline"}
            </span>
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                connected ? "bg-green-400" : "bg-muted-foreground"
              )}
            />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-72">
          {events.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No recent activity
            </p>
          ) : (
            <div className="divide-y">
              {events.map((event, i) => (
                <EventRow key={`${event.type}-${i}`} event={event} />
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
