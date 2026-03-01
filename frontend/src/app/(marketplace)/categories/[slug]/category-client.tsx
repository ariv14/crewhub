"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Bot } from "lucide-react";
import { useAgents } from "@/lib/hooks/use-agents";
import { AgentGrid } from "@/components/agents/agent-grid";
import { EmptyState } from "@/components/shared/empty-state";
import { CATEGORIES } from "@/lib/constants";
import { Button } from "@/components/ui/button";

export default function CategoryClient({ slug: serverSlug }: { slug: string }) {
  const params = useParams<{ slug: string }>();
  const slug = params.slug && params.slug !== "__fallback" ? params.slug : serverSlug;

  const category = CATEGORIES.find((c) => c.slug === slug);
  const label = category?.label ?? slug;

  const { data, isLoading } = useAgents({
    category: slug,
    status: "active",
    per_page: 50,
  });

  const agents = data?.agents ?? [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8">
        <Link
          href="/agents/"
          className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Marketplace
        </Link>
        <h1 className="text-3xl font-bold">{label}</h1>
        <p className="mt-2 text-muted-foreground">
          Agents in the {label} category
        </p>
      </div>

      {!isLoading && agents.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="No agents in this category"
          description="Check back later or browse all agents"
          action={
            <Button asChild variant="outline">
              <Link href="/agents/">Browse All Agents</Link>
            </Button>
          }
        />
      ) : (
        <AgentGrid agents={agents} loading={isLoading} />
      )}
    </div>
  );
}
