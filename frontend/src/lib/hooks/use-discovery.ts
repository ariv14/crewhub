import { useQuery } from "@tanstack/react-query";
import { searchAgents } from "../api/discovery";
import type { SearchQuery } from "@/types/discovery";

export function useDiscovery(query: Partial<SearchQuery>, enabled = true) {
  return useQuery({
    queryKey: ["discovery", query],
    queryFn: () => searchAgents(query),
    enabled: enabled && !!query.query,
  });
}
