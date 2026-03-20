// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { AlertTriangle, BadgeCheck, Clock, Play, Star, Zap } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { ROUTES, VERIFICATION_COLORS } from "@/lib/constants";
import { cn, formatCredits } from "@/lib/utils";
import { AgentSparkline } from "@/components/agents/agent-sparkline";
import { ActivityRing } from "@/components/agents/activity-ring";
import type { Agent } from "@/types/agent";

interface AgentCardProps {
  agent: Agent;
}

export function AgentCard({ agent }: AgentCardProps) {
  const defaultTier = agent.pricing.tiers.find((t) => t.is_default) ??
    agent.pricing.tiers[0];
  const price = defaultTier
    ? defaultTier.credits_per_unit
    : agent.pricing.credits;

  return (
    <a href={ROUTES.agentDetail(agent.id)} data-animate>
      <Card className="group h-full transition-all duration-200 hover:border-primary/50 hover:shadow-md hover:-translate-y-0.5">
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-2">
            <ActivityRing agentId={agent.id} status={agent.status} size="sm">
              <Avatar className="h-9 w-9 shrink-0">
                <AvatarImage src={agent.avatar_url ?? undefined} alt={agent.name} />
                <AvatarFallback className="text-xs font-medium">
                  {agent.name.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
            </ActivityRing>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h3 className="truncate font-semibold group-hover:text-primary">
                  {agent.name}
                </h3>
                {agent.status === "unavailable" && (
                  <Badge variant="outline" className="shrink-0 border-amber-500/30 text-amber-400 text-[10px] px-1.5 py-0">
                    Unavailable
                  </Badge>
                )}
                {agent.verification_level !== "new" && agent.status !== "unavailable" && (
                  <BadgeCheck
                    className={cn(
                      "h-4 w-4 shrink-0",
                      agent.verification_level === "certified"
                        ? "text-green-400"
                        : "text-blue-400"
                    )}
                  />
                )}
              </div>
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground/90">
                {agent.description}
              </p>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            <Badge variant="secondary" className="text-xs">
              {agent.category}
            </Badge>
            {agent.tags.slice(0, 2).map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        </CardContent>

        <CardFooter className="flex-col gap-2 border-t px-5 py-3">
          {/* Row 1: Stats */}
          <div className="flex w-full items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Star className="h-3 w-3 shrink-0 text-yellow-400" />
              {agent.reputation_score.toFixed(1)}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3 shrink-0" />
              {agent.avg_latency_ms < 1000
                ? `${agent.avg_latency_ms}ms`
                : `${(agent.avg_latency_ms / 1000).toFixed(1)}s`}
            </span>
            <span>{agent.total_tasks_completed} tasks</span>
            <span className="ml-auto opacity-50">
              <AgentSparkline agentId={agent.id} />
            </span>
          </div>
          {/* Row 2: Price + CTA */}
          <div className="flex w-full items-center justify-between">
            {agent.license_type === "open" || price === 0 ? (
              <Badge className="bg-green-600 text-white hover:bg-green-600 text-xs">
                FREE
              </Badge>
            ) : (
              <span className="flex items-center gap-1 text-xs font-medium text-foreground">
                <Zap className="h-3 w-3 shrink-0 text-primary" />
                {formatCredits(price)} credits
              </span>
            )}
            {agent.status === "unavailable" ? (
              <span className="inline-flex items-center gap-1 rounded-md border border-amber-500/30 px-2.5 py-1 text-xs text-amber-400">
                <AlertTriangle className="h-3 w-3" />
                Offline
              </span>
            ) : (
              <a
                href={`${ROUTES.agentDetail(agent.id)}?tab=try`}
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center gap-1 rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                data-testid="try-agent-button"
              >
                <Play className="h-3 w-3" />
                Try
              </a>
            )}
          </div>
        </CardFooter>
      </Card>
    </a>
  );
}
