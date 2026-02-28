import { Loader2 } from "lucide-react";
import { useAgents } from "@/lib/hooks/use-agents";
import { TryAgentPanel } from "@/components/agents/try-agent-panel";

interface StepTryAgentProps {
  interests: string[];
}

export function StepTryAgent({ interests }: StepTryAgentProps) {
  const category = interests[0] ?? undefined;
  const { data, isLoading } = useAgents({
    per_page: 1,
    category,
    status: "active",
  });

  const agent = data?.agents[0];

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold">Try an Agent</h2>
        <p className="mt-1 text-muted-foreground">
          Send a message to an agent and see how CrewHub works.
        </p>
      </div>
      {isLoading ? (
        <div className="flex min-h-[100px] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : agent ? (
        <div>
          <p className="mb-3 text-sm font-medium">{agent.name}</p>
          <TryAgentPanel agent={agent} />
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          No agents available to try right now. You can skip this step.
        </p>
      )}
    </div>
  );
}
