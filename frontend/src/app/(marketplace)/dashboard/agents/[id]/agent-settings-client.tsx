// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useParams, usePathname } from "next/navigation";
import { AgentSettings } from "@/components/agents/agent-settings";

function useFallbackId(serverId: string): string {
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  if (params.id && params.id !== "__fallback") return params.id;
  if (serverId && serverId !== "__fallback") return serverId;
  const seg = pathname.split("/").filter(Boolean).pop();
  return seg && seg !== "__fallback" ? seg : serverId;
}

export default function AgentSettingsClient({ id: serverId }: { id: string }) {
  const id = useFallbackId(serverId);
  return <AgentSettings agentId={id} />;
}
