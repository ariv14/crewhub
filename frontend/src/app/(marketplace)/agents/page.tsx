"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Bot, SlidersHorizontal } from "lucide-react";
import { useAgents } from "@/lib/hooks/use-agents";
import { useDiscovery } from "@/lib/hooks/use-discovery";
import { AgentGrid } from "@/components/agents/agent-grid";
import { AgentSearchBar } from "@/components/agents/agent-search-bar";
import {
  AgentFilters,
  type AgentFilterState,
} from "@/components/agents/agent-filters";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { CATEGORIES } from "@/lib/constants";
import { cn } from "@/lib/utils";

type AgentTypeFilter = "all" | "community" | "commercial";

export default function AgentsPage() {
  return (
    <Suspense>
      <AgentsPageContent />
    </Suspense>
  );
}

function AgentsPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [search, setSearch] = useState(searchParams.get("q") || "");
  const [page, setPage] = useState(
    Number(searchParams.get("page")) || 1
  );
  const [filters, setFilters] = useState<AgentFilterState>({
    category: searchParams.get("category") || "",
    minReputation: searchParams.get("minRep") || "",
    maxCredits: searchParams.get("maxCredits") || "",
    status: searchParams.get("status") || "active",
  });
  const [agentType, setAgentType] = useState<AgentTypeFilter>("all");
  const [filtersOpen, setFiltersOpen] = useState(false);

  const syncUrl = useCallback(
    (f: AgentFilterState, p: number, q?: string) => {
      const searchValue = q ?? search;
      const params = new URLSearchParams();
      if (searchValue) params.set("q", searchValue);
      if (f.category) params.set("category", f.category);
      if (f.minReputation) params.set("minRep", f.minReputation);
      if (f.maxCredits) params.set("maxCredits", f.maxCredits);
      if (f.status && f.status !== "active") params.set("status", f.status);
      if (p > 1) params.set("page", String(p));
      const qs = params.toString();
      router.replace(`/agents${qs ? `?${qs}` : ""}`, { scroll: false });
    },
    [router, search]
  );

  function handleFilterChange(f: AgentFilterState) {
    setFilters(f);
    setPage(1);
    syncUrl(f, 1);
  }

  function handleSearchChange(value: string) {
    setSearch(value);
    setPage(1);
    syncUrl(filters, 1, value);
  }

  // Use semantic search when query is 3+ chars, otherwise browse mode
  const useSemanticSearch = search.length >= 3;

  const { data, isLoading } = useAgents({
    page,
    per_page: 12,
    category: filters.category || undefined,
    status: filters.status || "active",
  });

  const { data: discoveryData, isLoading: discoveryLoading } = useDiscovery(
    {
      query: search,
      mode: "semantic",
      category: filters.category || undefined,
      max_credits: filters.maxCredits ? parseFloat(filters.maxCredits) : undefined,
      min_reputation: filters.minReputation ? parseFloat(filters.minReputation) : 0,
      limit: 20,
    },
    useSemanticSearch,
  );

  const isSearching = useSemanticSearch ? discoveryLoading : isLoading;

  const isFreeAgent = useCallback(
    (a: { license_type?: string; pricing: { credits: number } }) =>
      a.license_type === "open" || a.pricing.credits === 0,
    []
  );

  // Merge results: semantic search results or browse-mode with client-side filters
  const allAgents = useMemo(() => {
    if (useSemanticSearch && discoveryData) {
      return discoveryData.matches.map((m) => m.agent);
    }

    let result = data?.agents ?? [];

    // Reputation filter
    if (filters.minReputation) {
      const min = parseFloat(filters.minReputation);
      if (!isNaN(min)) {
        result = result.filter((a) => a.reputation_score >= min);
      }
    }

    // Credits filter
    if (filters.maxCredits) {
      const max = parseFloat(filters.maxCredits);
      if (!isNaN(max)) {
        result = result.filter((a) => a.pricing.credits <= max);
      }
    }

    return result;
  }, [data?.agents, useSemanticSearch, discoveryData, filters.minReputation, filters.maxCredits]);

  // Community/Commercial filter
  const agents = useMemo(() => {
    if (agentType === "community") return allAgents.filter(isFreeAgent);
    if (agentType === "commercial") return allAgents.filter((a) => !isFreeAgent(a));
    return allAgents;
  }, [allAgents, agentType, isFreeAgent]);

  const communityCount = useMemo(() => allAgents.filter(isFreeAgent).length, [allAgents, isFreeAgent]);
  const commercialCount = allAgents.length - communityCount;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Agent Marketplace</h1>
        <p className="mt-2 text-muted-foreground">
          Discover AI agents by capability, category, or intent
        </p>
      </div>

      <div className="mb-6">
        <AgentSearchBar
          value={search}
          onChange={handleSearchChange}
          onSubmit={() => syncUrl(filters, 1)}
        />
      </div>

      {/* Category quick links */}
      <div className="mb-4 flex gap-2 overflow-x-auto pb-1 scrollbar-none">
        {CATEGORIES.map((cat) => (
          <a
            key={cat.slug}
            href={`/categories/${cat.slug}/`}
            className={cn(
              "shrink-0 rounded-full border px-3 py-1 text-xs font-medium transition-colors hover:border-primary/40 hover:text-foreground",
              filters.category === cat.slug
                ? "border-primary bg-primary/10 text-foreground"
                : "text-muted-foreground"
            )}
          >
            {cat.label}
          </a>
        ))}
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {(
          [
            { key: "all", label: `All Agents (${allAgents.length})` },
            { key: "community", label: `Community \u2013 Free (${communityCount})` },
            { key: "commercial", label: `Commercial (${commercialCount})` },
          ] as const
        ).map(({ key, label }) => (
          <Button
            key={key}
            size="sm"
            variant={agentType === key ? "default" : "outline"}
            onClick={() => setAgentType(key)}
          >
            {label}
          </Button>
        ))}
      </div>

      {/* Mobile filters */}
      <div className="mb-4 lg:hidden">
        <Sheet open={filtersOpen} onOpenChange={setFiltersOpen}>
          <SheetTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <SlidersHorizontal className="h-4 w-4" />
              Filters
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-80">
            <SheetHeader>
              <SheetTitle>Filters</SheetTitle>
            </SheetHeader>
            <div className="mt-6">
              <AgentFilters filters={filters} onChange={(f) => { handleFilterChange(f); setFiltersOpen(false); }} />
            </div>
          </SheetContent>
        </Sheet>
      </div>

      <div className="flex gap-8">
        <div className="hidden w-56 shrink-0 lg:block">
          <AgentFilters filters={filters} onChange={handleFilterChange} />
        </div>

        <div className="min-w-0 flex-1">
          {!isSearching && agents.length === 0 ? (
            <EmptyState
              icon={Bot}
              title="No agents found"
              description="Try adjusting your filters or search terms"
            />
          ) : (
            <AgentGrid agents={agents} loading={isSearching} />
          )}

          {!useSemanticSearch && data && data.total > 12 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => {
                  const p = page - 1;
                  setPage(p);
                  syncUrl(filters, p);
                }}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {Math.ceil(data.total / 12)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= Math.ceil(data.total / 12)}
                onClick={() => {
                  const p = page + 1;
                  setPage(p);
                  syncUrl(filters, p);
                }}
              >
                Next
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
