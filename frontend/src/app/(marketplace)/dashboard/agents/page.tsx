"use client";

import Link from "next/link";
import { Bot, Plus, Settings } from "lucide-react";
import { useAgents } from "@/lib/hooks/use-agents";
import { useAuth } from "@/lib/auth-context";
import { ROUTES, AGENT_STATUS_COLORS } from "@/lib/constants";
import { cn, formatCredits, formatRelativeTime } from "@/lib/utils";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function MyAgentsPage() {
  const { user } = useAuth();
  const { data, isLoading } = useAgents(
    user ? { owner_id: user.id } : undefined
  );
  const agents = data?.agents ?? [];

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Agents</h1>
          <p className="mt-1 text-muted-foreground">
            Manage your registered agents
          </p>
        </div>
        <Button asChild>
          <Link href={ROUTES.registerAgent}>
            <Plus className="mr-2 h-4 w-4" />
            Register Agent
          </Link>
        </Button>
      </div>

      <div className="mt-6">
        {!isLoading && agents.length === 0 ? (
          <EmptyState
            icon={Bot}
            title="No agents registered"
            description="Register your first AI agent on the marketplace"
            action={
              <Button asChild>
                <Link href={ROUTES.registerAgent}>Register Agent</Link>
              </Button>
            }
          />
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Tasks</TableHead>
                  <TableHead>Reputation</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="w-[80px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agents.map((agent) => (
                  <TableRow key={agent.id}>
                    <TableCell>
                      <a
                        href={ROUTES.agentDetail(agent.id)}
                        className="font-medium hover:text-primary hover:underline"
                      >
                        {agent.name}
                      </a>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {agent.category}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-xs capitalize",
                          AGENT_STATUS_COLORS[agent.status]
                        )}
                      >
                        {agent.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">
                      {agent.total_tasks_completed}
                    </TableCell>
                    <TableCell className="text-sm">
                      {agent.reputation_score.toFixed(1)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatRelativeTime(agent.created_at)}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" asChild>
                        <a href={ROUTES.agentSettings(agent.id)}>
                          <Settings className="h-4 w-4" />
                        </a>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}
