"use client";

import { use } from "react";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useAgent } from "@/lib/hooks/use-agents";
import { ROUTES } from "@/lib/constants";
import { AgentDetailHeader } from "@/components/agents/agent-detail-header";
import { AgentSkillsList } from "@/components/agents/agent-skills-list";
import { AgentPricingTable } from "@/components/agents/agent-pricing-table";
import { JsonViewer } from "@/components/shared/json-viewer";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function AdminAgentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: agent, isLoading } = useAgent(id);

  if (isLoading || !agent) {
    return (
      <div className="flex min-h-[300px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
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
