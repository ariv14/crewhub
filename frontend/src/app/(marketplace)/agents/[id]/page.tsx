import AgentDetailClient from "./agent-detail-client";

export function generateStaticParams() {
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
