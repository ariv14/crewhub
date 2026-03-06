"use client";

import { useParams } from "next/navigation";
import { AgentSettings } from "@/components/agents/agent-settings";

export default function AgentSettingsPage() {
  const params = useParams<{ id: string }>();
  return <AgentSettings agentId={params.id} />;
}
