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
  credit_transaction: { icon: CreditCard, label: "Credit transaction", color: "text-amber-500" },
};

function formatRelativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ago`;
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
    <div className="flex items-center gap-3 py-2">
      <div className="relative">
        <Icon className={cn("h-4 w-4", config.color)} />
        {isRecent && (
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 animate-pulse rounded-full bg-green-400" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm">{config.label}</p>
        {event.name && (
          <p className="truncate text-xs text-muted-foreground">
            {event.name as string}
          </p>
        )}
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
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              connected ? "bg-green-400" : "bg-muted-foreground"
            )}
            title={connected ? "Connected" : "Disconnected"}
          />
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-64">
          {events.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Waiting for activity...
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
