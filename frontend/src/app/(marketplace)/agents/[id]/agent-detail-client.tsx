"use client";

import { ArrowLeft, CheckCircle2, Copy, Loader2, XCircle } from "lucide-react";
import Link from "next/link";
import { useAgent, useAgentCard } from "@/lib/hooks/use-agents";
import { AgentDetailHeader } from "@/components/agents/agent-detail-header";
import { AgentSkillsList } from "@/components/agents/agent-skills-list";
import { AgentPricingTable } from "@/components/agents/agent-pricing-table";
import { TryAgentPanel } from "@/components/agents/try-agent-panel";
import { JsonViewer } from "@/components/shared/json-viewer";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function AgentDetailClient({ id }: { id: string }) {
  const { data: agent, isLoading, error } = useAgent(id);
  const { data: a2aCard } = useAgentCard(id);

  if (isLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 text-center">
        <h1 className="text-2xl font-bold">Agent not found</h1>
        <p className="mt-2 text-muted-foreground">
          This agent may have been removed or the ID is invalid.
        </p>
        <Button variant="outline" className="mt-4" asChild>
          <Link href="/agents">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Marketplace
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Button variant="ghost" size="sm" className="mb-4" asChild>
        <Link href="/agents">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Marketplace
        </Link>
      </Button>

      <AgentDetailHeader agent={agent} />

      <Tabs defaultValue="overview" className="mt-8">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="skills">
            Skills ({agent.skills.length})
          </TabsTrigger>
          <TabsTrigger value="pricing">Pricing</TabsTrigger>
          <TabsTrigger value="try">Try It</TabsTrigger>
          <TabsTrigger value="a2a-card">A2A Card</TabsTrigger>
          <TabsTrigger value="protocols">Protocols</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6 space-y-6">
          <div>
            <h2 className="mb-3 text-lg font-semibold">Description</h2>
            <p className="whitespace-pre-wrap text-muted-foreground">
              {agent.description}
            </p>
          </div>

          {agent.sla && (
            <div>
              <h2 className="mb-3 text-lg font-semibold">SLA</h2>
              <div className="flex gap-6 text-sm">
                {agent.sla.max_latency_ms != null && (
                  <div>
                    <p className="text-muted-foreground">Max Latency</p>
                    <p className="font-medium">{agent.sla.max_latency_ms}ms</p>
                  </div>
                )}
                {agent.sla.uptime_guarantee != null && (
                  <div>
                    <p className="text-muted-foreground">Uptime Guarantee</p>
                    <p className="font-medium">
                      {agent.sla.uptime_guarantee}%
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          <div>
            <h2 className="mb-3 text-lg font-semibold">Payment Methods</h2>
            <div className="flex gap-2">
              {agent.accepted_payment_methods.map((method) => (
                <span
                  key={method}
                  className="rounded-md border px-3 py-1 text-sm capitalize"
                >
                  {method}
                </span>
              ))}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="skills" className="mt-6">
          <AgentSkillsList skills={agent.skills} />
        </TabsContent>

        <TabsContent value="pricing" className="mt-6">
          <AgentPricingTable pricing={agent.pricing} />
        </TabsContent>

        <TabsContent value="try" className="mt-6">
          <TryAgentPanel agent={agent} />
        </TabsContent>

        <TabsContent value="a2a-card" className="mt-6">
          {a2aCard ? (
            <JsonViewer data={a2aCard} title="A2A Agent Card" />
          ) : (
            <p className="text-sm text-muted-foreground">Loading A2A card...</p>
          )}
        </TabsContent>

        <TabsContent value="protocols" className="mt-6">
          <div className="space-y-6">
            <h2 className="text-lg font-semibold">Protocol Support</h2>

            {/* A2A */}
            <div className="rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">A2A (Agent-to-Agent)</h3>
                  <p className="text-sm text-muted-foreground">
                    JSON-RPC task lifecycle with SSE streaming
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {agent.endpoint ? (
                    <>
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                      <span className="text-sm text-green-600">Active</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-5 w-5 text-red-500" />
                      <span className="text-sm text-red-600">Not configured</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* MCP */}
            <div className="rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">MCP (Model Context Protocol)</h3>
                  <p className="text-sm text-muted-foreground">
                    Tool exposure for LLM integrations
                  </p>
                  {agent.mcp_server_url && (
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      {agent.mcp_server_url}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {agent.mcp_server_url ? (
                    <>
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                      <span className="text-sm text-green-600">Active</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-5 w-5 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Not set</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* ANP / DID */}
            <div className="rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">ANP (Agent Network Protocol)</h3>
                  <p className="text-sm text-muted-foreground">
                    Decentralized identity with DID:wba
                  </p>
                  {agent.did && (
                    <div className="mt-1 flex items-center gap-2">
                      <code className="rounded bg-muted px-2 py-0.5 font-mono text-xs">
                        {agent.did}
                      </code>
                      <button
                        onClick={() => navigator.clipboard.writeText(agent.did!)}
                        className="text-muted-foreground hover:text-foreground"
                        title="Copy DID"
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {agent.did ? (
                    <>
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                      <span className="text-sm text-green-600">Verified</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-5 w-5 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">No identity</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
