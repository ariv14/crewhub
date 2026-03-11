import { api } from "../api-client";
import type { DiscoveryResponse, SearchQuery } from "@/types/discovery";

export async function searchAgents(
  query: Partial<SearchQuery>
): Promise<DiscoveryResponse> {
  return api.post("/discover/", {
    query: query.query || "",
    mode: query.mode || "keyword",
    category: query.category,
    tags: query.tags || [],
    max_latency_ms: query.max_latency_ms,
    max_credits: query.max_credits,
    input_modes: query.input_modes || [],
    output_modes: query.output_modes || [],
    min_reputation: query.min_reputation || 0,
    limit: query.limit || 10,
  });
}

export async function getRecommendations(agentId: string): Promise<DiscoveryResponse> {
  return api.get(`/discover/recommend/${agentId}`);
}
