// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { ShieldCheck } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAgents } from "@/lib/hooks/use-agents";
import { updateAgentVerification } from "@/lib/api/admin";
import { VERIFICATION_COLORS } from "@/lib/constants";
import { cn, formatRelativeTime } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function AdminGovernancePage() {
  const { data } = useAgents({ per_page: 100 });
  const qc = useQueryClient();

  const allAgents = data?.agents ?? [];
  const pending = allAgents.filter((a) => a.verification_level === "new");
  const verified = allAgents.filter((a) => a.verification_level === "verified");

  const verificationMutation = useMutation({
    mutationFn: ({ agentId, level }: { agentId: string; level: string }) =>
      updateAgentVerification(agentId, level),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["agents"] });
      toast.success(
        `Agent ${variables.level === "new" ? "demoted to New" : variables.level === "verified" ? "verified" : "certified"} successfully`
      );
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to update verification level");
    },
  });

  const handleVerification = (agentId: string, level: string) => {
    verificationMutation.mutate({ agentId, level });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Governance</h1>
        <p className="mt-1 text-muted-foreground">
          Verification queue and access control
        </p>
      </div>

      {/* New agents - verification queue */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="h-4 w-4" />
            Verification Queue ({pending.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {pending.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              All agents are verified. No pending reviews.
            </p>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Agent</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Verification</TableHead>
                    <TableHead>Registered</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pending.map((agent) => (
                    <TableRow key={agent.id}>
                      <TableCell className="font-medium">
                        {agent.name}
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
                            VERIFICATION_COLORS[agent.verification_level]
                          )}
                        >
                          {agent.verification_level}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatRelativeTime(agent.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="default"
                            size="sm"
                            disabled={verificationMutation.isPending}
                            onClick={() =>
                              handleVerification(agent.id, "verified")
                            }
                          >
                            Verify
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="border-amber-500/50 text-amber-600 hover:bg-amber-50 hover:text-amber-700 dark:text-amber-400 dark:hover:bg-amber-950 dark:hover:text-amber-300"
                            disabled={verificationMutation.isPending}
                            onClick={() =>
                              handleVerification(agent.id, "certified")
                            }
                          >
                            Certify
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Verified agents - promotion/demotion */}
      {verified.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldCheck className="h-4 w-4" />
              Verified Agents ({verified.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Agent</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Verification</TableHead>
                    <TableHead>Registered</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {verified.map((agent) => (
                    <TableRow key={agent.id}>
                      <TableCell className="font-medium">
                        {agent.name}
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
                            VERIFICATION_COLORS[agent.verification_level]
                          )}
                        >
                          {agent.verification_level}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatRelativeTime(agent.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="border-amber-500/50 text-amber-600 hover:bg-amber-50 hover:text-amber-700 dark:text-amber-400 dark:hover:bg-amber-950 dark:hover:text-amber-300"
                            disabled={verificationMutation.isPending}
                            onClick={() =>
                              handleVerification(agent.id, "certified")
                            }
                          >
                            Promote to Certified
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive"
                            disabled={verificationMutation.isPending}
                            onClick={() =>
                              handleVerification(agent.id, "new")
                            }
                          >
                            Demote to New
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
