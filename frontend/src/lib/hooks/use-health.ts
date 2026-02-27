import { useQuery } from "@tanstack/react-query";
import { getHealth } from "../api/health";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 30000, // Poll every 30s
  });
}
