import {
  BadgeCheck,
  Clock,
  ExternalLink,
  Star,
  Zap,
} from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AGENT_STATUS_COLORS,
  VERIFICATION_COLORS,
} from "@/lib/constants";
import { cn, formatCredits } from "@/lib/utils";
import { ActivityRing } from "@/components/agents/activity-ring";
import type { Agent } from "@/types/agent";
import Link from "next/link";

interface AgentDetailHeaderProps {
  agent: Agent;
}

export function AgentDetailHeader({ agent }: AgentDetailHeaderProps) {
  const defaultTier = agent.pricing.tiers.find((t) => t.is_default) ??
    agent.pricing.tiers[0];
  const price = defaultTier
    ? defaultTier.credits_per_unit
    : agent.pricing.credits;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 flex-1 gap-4">
          <ActivityRing agentId={agent.id} status={agent.status} size="lg">
            <Avatar className="h-14 w-14 shrink-0">
              <AvatarImage src={agent.avatar_url ?? undefined} alt={agent.name} />
              <AvatarFallback className="text-lg font-semibold">
                {agent.name.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
          </ActivityRing>
          <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{agent.name}</h1>
            {agent.verification_level !== "new" && (
              <Badge
                variant="outline"
                className={cn(
                  "gap-1",
                  VERIFICATION_COLORS[agent.verification_level]
                )}
              >
                <BadgeCheck className="h-3 w-3" />
                {agent.verification_level}
              </Badge>
            )}
            <Badge
              variant="outline"
              className={cn(AGENT_STATUS_COLORS[agent.status])}
            >
              {agent.status}
            </Badge>
          </div>
          <p className="mt-2 text-muted-foreground">{agent.description}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <Badge variant="secondary">{agent.category}</Badge>
            {agent.tags.map((tag) => (
              <Badge key={tag} variant="outline">
                {tag}
              </Badge>
            ))}
          </div>
          </div>
        </div>

        <div className="shrink-0 text-right">
          <p className="text-sm text-muted-foreground">Starting at</p>
          <p className="text-2xl font-bold">
            {formatCredits(price)}{" "}
            <span className="text-sm font-normal text-muted-foreground">
              credits
            </span>
          </p>
          <Button className="mt-3" asChild>
            <Link href={`/dashboard/tasks/new?agent=${agent.id}`}>
              <Zap className="mr-2 h-4 w-4" />
              Delegate Task
            </Link>
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-6 border-t pt-4 text-sm text-muted-foreground">
        <span className="flex items-center gap-1">
          <Star className="h-4 w-4 text-yellow-400" />
          <strong className="text-foreground">
            {agent.reputation_score.toFixed(1)}
          </strong>{" "}
          reputation
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-4 w-4" />
          {agent.avg_latency_ms < 1000
            ? `${Math.round(agent.avg_latency_ms)}ms`
            : `${(agent.avg_latency_ms / 1000).toFixed(1)}s`}{" "}
          avg latency
        </span>
        <span>
          <strong className="text-foreground">
            {agent.total_tasks_completed}
          </strong>{" "}
          tasks completed
        </span>
        <span>
          <strong className="text-foreground">
            {(agent.success_rate * 100).toFixed(0)}%
          </strong>{" "}
          success rate
        </span>
        <span className="flex items-center gap-1">
          v{agent.version}
        </span>
      </div>
    </div>
  );
}
