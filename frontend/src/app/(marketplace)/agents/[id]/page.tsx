import { API_V1 } from "@/lib/constants";
import AgentDetailClient from "./agent-detail-client";

export const dynamicParams = false;

export async function generateStaticParams() {
  // Fetch all agent IDs at build time so each gets a pre-rendered page.
  // This is required because dynamicParams:false (needed for static export)
  // rejects any param not returned here.
  try {
    const res = await fetch(`${API_V1}/agents/?per_page=200`);
    if (res.ok) {
      const data = await res.json();
      const agents: { id: string }[] = (data.agents ?? data).map(
        (a: { id: string }) => ({ id: a.id })
      );
      // Keep the "_" shell as a fallback for agents added post-build
      return [{ id: "_" }, ...agents];
    }
  } catch {
    // Build continues with just the shell page if API is unreachable
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
