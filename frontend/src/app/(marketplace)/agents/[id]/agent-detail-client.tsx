// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState, useEffect } from "react";
import { ArrowLeft, CheckCircle2, ChevronRight, Copy, Settings, XCircle } from "lucide-react";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import Link from "next/link";
import { useParams, usePathname, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAgent, useAgentCard } from "@/lib/hooks/use-agents";
import { getRecommendations } from "@/lib/api/discovery";
import { AgentDetailHeader } from "@/components/agents/agent-detail-header";
import { AgentActivityTab } from "@/components/agents/agent-activity-tab";
import { AgentSkillsList } from "@/components/agents/agent-skills-list";
import { AgentPricingTable } from "@/components/agents/agent-pricing-table";
import { AgentCard } from "@/components/agents/agent-card";
import { TryAgentPanel } from "@/components/agents/try-agent-panel";
import { JsonViewer } from "@/components/shared/json-viewer";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/lib/auth-context";
import { CATEGORIES, ROUTES } from "@/lib/constants";

function useAgentId(serverId: string): string {
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  if (params.id && params.id !== "__fallback") return params.id;
  if (serverId && serverId !== "__fallback") return serverId;
  // Cloudflare rewrite serves __fallback HTML at the real URL — extract ID from path.
  const seg = pathname.split("/").filter(Boolean).pop();
  return seg && seg !== "__fallback" ? seg : serverId;
}

export default function AgentDetailClient({ id: serverId }: { id: string }) {
  const id = useAgentId(serverId);

  const searchParams = useSearchParams();
  const { data: agent, isLoading, error } = useAgent(id);
  const { data: a2aCard } = useAgentCard(id);
  const { data: recommendations } = useQuery({
    queryKey: ["agents", id, "recommendations"],
    queryFn: () => getRecommendations(id),
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
  });
  const { user } = useAuth();
  const isOwner = !!(user && agent?.owner_id === user.id);
  const defaultTab = searchParams.get("tab") || "overview";
  const [activeTab, setActiveTab] = useState(defaultTab);

  // Sync tab from URL params (enables deep-linking like ?tab=try)
  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab) setActiveTab(tab);
  }, [searchParams]);

  if (isLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <SpinningLogo spinning size="lg" />
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
          <a href="/agents">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Marketplace
          </a>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl overflow-x-hidden px-4 py-8">
      <nav className="mb-4 flex items-center gap-1 text-sm" aria-label="Breadcrumb">
        <a href="/agents" className="text-muted-foreground hover:text-foreground">
          Marketplace
        </a>
        {agent.category && (
          <>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
            <a
              href={`/categories/${agent.category}/`}
              className="text-muted-foreground hover:text-foreground"
            >
              {CATEGORIES.find((c) => c.slug === agent.category)?.label ?? agent.category}
            </a>
          </>
        )}
        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="font-medium truncate max-w-[200px]">{agent.name}</span>
      </nav>

      {isOwner && (
        <Button variant="outline" size="sm" className="mb-4" asChild>
          <a href={ROUTES.agentSettings(agent.id)}>
            <Settings className="mr-2 h-4 w-4" />
            Manage Agent
          </a>
        </Button>
      )}

      <AgentDetailHeader agent={agent} isAuthenticated={!!user} />

      <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-8">
        <TabsList className="flex w-full overflow-x-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="try">Try It</TabsTrigger>
          <TabsTrigger value="skills">
            Skills ({agent.skills.length})
          </TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="developer">Developer</TabsTrigger>
        </TabsList>

        {/* Overview — includes description, SLA, payment methods, and pricing */}
        <TabsContent value="overview" className="mt-6 space-y-6">
          <div>
            <h2 className="mb-3 text-lg font-semibold">Description</h2>
            <p className="whitespace-pre-wrap text-muted-foreground">
              {agent.description}
            </p>
          </div>

          {agent.sla && (agent.sla.max_latency_ms != null || agent.sla.uptime_guarantee != null) && (
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

          <div>
            <h2 className="mb-3 text-lg font-semibold">Pricing</h2>
            <AgentPricingTable pricing={agent.pricing} />
          </div>
        </TabsContent>

        {/* Try It — positioned 2nd so it's always visible on mobile */}
        <TabsContent value="try" className="mt-6">
          <TryAgentPanel
            key={agent.id}
            agent={agent}
            initialMessage={searchParams.get("message") ?? undefined}
          />
        </TabsContent>

        <TabsContent value="skills" className="mt-6">
          <AgentSkillsList skills={agent.skills} />
        </TabsContent>

        <TabsContent value="activity" className="mt-6">
          <AgentActivityTab agent={agent} isOwner={isOwner} />
        </TabsContent>

        {/* Developer — merged A2A Card + Protocol Support */}
        <TabsContent value="developer" className="mt-6 space-y-6">
          {a2aCard && (
            <div>
              <JsonViewer data={a2aCard} title="A2A Agent Card" />
            </div>
          )}

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
                        aria-label="Copy DID"
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

      {/* Similar Agents */}
      {recommendations && recommendations.matches.length > 0 && (
        <div className="mt-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">You might also like</h2>
            <Link href="/agents" className="text-sm text-muted-foreground hover:text-primary">
              View all →
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {recommendations.matches.slice(0, 4).map((match) => (
              <AgentCard key={match.agent.id} agent={match.agent} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
