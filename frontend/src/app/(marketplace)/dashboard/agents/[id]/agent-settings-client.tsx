"use client";

import { useParams } from "next/navigation";
import { AgentSettings } from "@/components/agents/agent-settings";

export default function AgentSettingsClient({ id: serverId }: { id: string }) {
  const params = useParams<{ id: string }>();
  const id = params.id && params.id !== "__fallback" ? params.id : serverId;
  return <AgentSettings agentId={id} />;
}
