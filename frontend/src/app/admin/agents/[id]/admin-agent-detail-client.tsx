// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useAgent } from "@/lib/hooks/use-agents";
import { ROUTES } from "@/lib/constants";
import { AgentDetailHeader } from "@/components/agents/agent-detail-header";
import { AgentSkillsList } from "@/components/agents/agent-skills-list";
import { AgentPricingTable } from "@/components/agents/agent-pricing-table";
import { JsonViewer } from "@/components/shared/json-viewer";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function AdminAgentDetailClient({ id: serverId }: { id: string }) {
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  const pathId = pathname.split("/").filter(Boolean).pop();
  const id =
    (params.id && params.id !== "__fallback" ? params.id : null) ??
    (serverId && serverId !== "__fallback" ? serverId : null) ??
    (pathId && pathId !== "__fallback" ? pathId : null) ??
    serverId;

  const { data: agent, isLoading, isError } = useAgent(id);

  if (isLoading) {
    return (
      <div className="flex min-h-[300px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isError || !agent) {
    return (
      <div className="flex min-h-[300px] flex-col items-center justify-center gap-4 text-center">
        <h2 className="text-lg font-semibold">Agent not found</h2>
        <p className="text-sm text-muted-foreground">
          This agent may have been deleted or the ID is invalid.
        </p>
        <Button variant="outline" asChild>
          <Link href={ROUTES.adminAgents}>
            <ArrowLeft className="mr-1 h-3.5 w-3.5" />
            Back to Agents
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild>
        <Link href={ROUTES.adminAgents}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Agents
        </Link>
      </Button>

      <AgentDetailHeader agent={agent} />

      <Tabs defaultValue="skills">
        <TabsList>
          <TabsTrigger value="skills">Skills</TabsTrigger>
          <TabsTrigger value="pricing">Pricing</TabsTrigger>
          <TabsTrigger value="raw">Raw Data</TabsTrigger>
        </TabsList>
        <TabsContent value="skills" className="mt-4">
          <AgentSkillsList skills={agent.skills} />
        </TabsContent>
        <TabsContent value="pricing" className="mt-4">
          <AgentPricingTable pricing={agent.pricing} />
        </TabsContent>
        <TabsContent value="raw" className="mt-4">
          <JsonViewer data={agent} title="Agent JSON" />
        </TabsContent>
      </Tabs>
    </div>
  );
}
