import { API_V1 } from "@/lib/constants";
import AgentDetailClient from "./agent-detail-client";

export const dynamicParams = false;

export async function generateStaticParams() {
  const url = `${API_V1}/agents/?per_page=100`;
  console.log(`[generateStaticParams] Fetching agents from: ${url}`);
  try {
    const res = await fetch(url);
    console.log(`[generateStaticParams] Response status: ${res.status}`);
    if (res.ok) {
      const data = await res.json();
      const agents: { id: string }[] = (data.agents ?? data).map(
        (a: { id: string }) => ({ id: a.id })
      );
      console.log(`[generateStaticParams] Found ${agents.length} agents`);
      return [{ id: "_" }, ...agents];
    }
  } catch (e) {
    console.error(`[generateStaticParams] Error:`, e);
  }
  return [{ id: "_" }];
}

export default async function AgentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AgentDetailClient id={id} />;
}
