"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { Agent } from "@/types/agent";

interface AgentStatusBoardProps {
  myAgents: Agent[];
  publicAgents: Agent[];
}

const STATUS_STYLES: Record<string, string> = {
  active: "bg-green-500/15 text-green-400 border-green-500/20",
  inactive: "bg-gray-500/15 text-gray-400 border-gray-500/20",
  suspended: "bg-red-500/15 text-red-400 border-red-500/20",
};

function AgentRow({ agent, showTasks }: { agent: Agent; showTasks?: boolean }) {
  const statusStyle = STATUS_STYLES[agent.status] ?? STATUS_STYLES.active;
  return (
    <a
      href={ROUTES.agentDetail(agent.id)}
      className="flex items-center gap-3 rounded-md px-2 py-2 transition-colors hover:bg-muted/50"
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted text-xs font-medium">
        {agent.avatar_url ? (
          <img src={agent.avatar_url} alt="" className="h-8 w-8 rounded-md object-cover" />
        ) : (
          agent.name.charAt(0).toUpperCase()
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{agent.name}</p>
        <p className="text-xs text-muted-foreground">
          {agent.skills.length} skill{agent.skills.length !== 1 ? "s" : ""}
          {showTasks && agent.total_tasks_completed > 0 && (
            <span> &middot; {agent.total_tasks_completed} task{agent.total_tasks_completed !== 1 ? "s" : ""} done</span>
          )}
          {!showTasks && (
            <span> &middot; {agent.category}</span>
          )}
        </p>
      </div>
      <Badge
        variant="outline"
        className={cn("shrink-0 text-[10px] px-1.5 py-0", statusStyle)}
      >
        {agent.status}
      </Badge>
    </a>
  );
}

export function AgentStatusBoard({ myAgents, publicAgents }: AgentStatusBoardProps) {
  const hasOwn = myAgents.length > 0;
  const hasPublic = publicAgents.length > 0;

  if (!hasOwn && !hasPublic) return null;

  return (
    <Card>
      {/* My Agents Section */}
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">My Agents</CardTitle>
          {hasOwn && (
            <a
              href={ROUTES.myAgents}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Manage
            </a>
          )}
        </div>
      </CardHeader>
      <CardContent className="pb-2">
        {hasOwn ? (
          <div className="space-y-0.5">
            {myAgents.slice(0, 5).map((agent) => (
              <AgentRow key={agent.id} agent={agent} showTasks />
            ))}
            {myAgents.length > 5 && (
              <p className="pt-1 text-center text-xs text-muted-foreground">
                +{myAgents.length - 5} more
              </p>
            )}
          </div>
        ) : (
          <p className="py-3 text-center text-sm text-muted-foreground">
            No agents yet.{" "}
            <a href={ROUTES.registerAgent} className="text-primary hover:underline">
              Register one
            </a>
          </p>
        )}
      </CardContent>

      {/* Marketplace Highlights */}
      {hasPublic && (
        <>
          <Separator />
          <CardHeader className="pb-2 pt-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Popular on Marketplace</CardTitle>
              <a
                href={ROUTES.agents}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Browse all
              </a>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-0.5">
              {publicAgents.slice(0, 4).map((agent) => (
                <AgentRow key={agent.id} agent={agent} />
              ))}
            </div>
          </CardContent>
        </>
      )}
    </Card>
  );
}
