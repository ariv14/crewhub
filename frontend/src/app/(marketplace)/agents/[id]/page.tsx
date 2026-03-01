import AgentDetailClient from "./agent-detail-client";

export const dynamicParams = false;

export async function generateStaticParams() {
  // Static export: generate a single shell page; actual agent data is fetched client-side.
  // The [id] catch-all renders for any UUID via client-side routing.
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
