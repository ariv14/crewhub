import { Loader2 } from "lucide-react";
import { useAgents } from "@/lib/hooks/use-agents";
import { AgentCard } from "@/components/agents/agent-card";

interface StepRecommendedProps {
  interests: string[];
}

export function StepRecommended({ interests }: StepRecommendedProps) {
  const category = interests[0] ?? undefined;
  const { data, isLoading } = useAgents({
    per_page: 4,
    category,
    status: "active",
  });

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold">Recommended Agents</h2>
        <p className="mt-1 text-muted-foreground">
          Based on your interests, here are some agents you might like.
        </p>
      </div>
      {isLoading ? (
        <div className="flex min-h-[100px] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {(data?.agents ?? []).slice(0, 4).map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
          {data?.agents.length === 0 && (
            <p className="col-span-2 text-center text-sm text-muted-foreground">
              No agents found for your interests yet. You can browse the
              marketplace after onboarding.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
