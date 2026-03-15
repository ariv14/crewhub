// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import AgentSettingsClient from "./agent-settings-client";

export const dynamicParams = false;

export function generateStaticParams() {
  // Agent IDs aren't known at build time — use a fallback.
  // Cloudflare _redirects rewrites /dashboard/agents/:id to this page.
  return [{ id: "__fallback" }];
}

export default async function AgentSettingsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AgentSettingsClient id={id} />;
}
