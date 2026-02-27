import Link from "next/link";
import { BadgeCheck, Clock, Star, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { ROUTES, VERIFICATION_COLORS } from "@/lib/constants";
import { cn, formatCredits } from "@/lib/utils";
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
    <Link href={ROUTES.agentDetail(agent.id)}>
      <Card className="group h-full transition-colors hover:border-primary/50">
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h3 className="truncate font-semibold group-hover:text-primary">
                  {agent.name}
                </h3>
                {agent.verification_level !== "unverified" && (
                  <BadgeCheck
                    className={cn(
                      "h-4 w-4 shrink-0",
                      agent.verification_level === "audit"
                        ? "text-green-400"
                        : agent.verification_level === "quality"
                          ? "text-purple-400"
                          : "text-blue-400"
                    )}
                  />
                )}
              </div>
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
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

        <CardFooter className="border-t px-5 py-3">
          <div className="flex w-full items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <Star className="h-3 w-3 text-yellow-400" />
                {agent.reputation_score.toFixed(1)}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {agent.avg_latency_ms < 1000
                  ? `${agent.avg_latency_ms}ms`
                  : `${(agent.avg_latency_ms / 1000).toFixed(1)}s`}
              </span>
              <span>{agent.total_tasks_completed} tasks</span>
            </div>
            <span className="flex items-center gap-1 font-medium text-foreground">
              <Zap className="h-3 w-3 text-primary" />
              {formatCredits(price)} credits
            </span>
          </div>
        </CardFooter>
      </Card>
    </Link>
  );
}
