"use client";

import Link from "next/link";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ActivityRing } from "@/components/agents/activity-ring";
import { useAgentActivity } from "@/lib/hooks/use-agent-activity";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { Agent } from "@/types/agent";

interface AgentStatusBoardProps {
  agents: Agent[];
}

export function AgentStatusBoard({ agents }: AgentStatusBoardProps) {
  const { connected } = useAgentActivity();

  if (agents.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Agent Status</CardTitle>
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              connected ? "bg-green-400" : "bg-muted-foreground",
            )}
            title={connected ? "Live" : "Offline"}
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-4">
          {agents.map((agent) => (
            <Link
              key={agent.id}
              href={ROUTES.agentDetail(agent.id)}
              className="group flex flex-col items-center gap-1.5"
              title={agent.name}
            >
              <ActivityRing
                agentId={agent.id}
                status={agent.status}
                size="md"
              >
                <Avatar className="h-10 w-10">
                  <AvatarImage
                    src={agent.avatar_url ?? undefined}
                    alt={agent.name}
                  />
                  <AvatarFallback className="text-sm font-medium">
                    {agent.name.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
              </ActivityRing>
              <span className="max-w-[4rem] truncate text-xs text-muted-foreground group-hover:text-foreground">
                {agent.name.split(" ")[0]}
              </span>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
