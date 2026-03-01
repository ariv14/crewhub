import AgentDetailClient from "./agent-detail-client";

export const dynamicParams = true;

export async function generateStaticParams() {
  // Agent IDs are fetched client-side; return empty so static export succeeds
  return [];
}

export default async function AgentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AgentDetailClient id={id} />;
}
