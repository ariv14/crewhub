"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Bot } from "lucide-react";
import { useAgents } from "@/lib/hooks/use-agents";
import { AgentGrid } from "@/components/agents/agent-grid";
import { AgentSearchBar } from "@/components/agents/agent-search-bar";
import {
  AgentFilters,
  type AgentFilterState,
} from "@/components/agents/agent-filters";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";

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

  const { data, isLoading } = useAgents({
    page,
    per_page: 12,
    category: filters.category || undefined,
    status: filters.status || "active",
    q: search || undefined,
  });

  // Client-side post-filtering for search, reputation, and credits
  const agents = useMemo(() => {
    let result = data?.agents ?? [];

    // Client-side name/description filter (fallback if API doesn't support q)
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (a) =>
          a.name.toLowerCase().includes(q) ||
          a.description.toLowerCase().includes(q)
      );
    }

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
  }, [data?.agents, search, filters.minReputation, filters.maxCredits]);

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

      <div className="flex gap-8">
        <div className="hidden w-56 shrink-0 lg:block">
          <AgentFilters filters={filters} onChange={handleFilterChange} />
        </div>

        <div className="min-w-0 flex-1">
          {!isLoading && agents.length === 0 ? (
            <EmptyState
              icon={Bot}
              title="No agents found"
              description="Try adjusting your filters or search terms"
            />
          ) : (
            <AgentGrid agents={agents} loading={isLoading} />
          )}

          {data && data.total > 12 && (
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
