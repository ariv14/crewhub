import AdminAgentDetailClient from "./admin-agent-detail-client";

export function generateStaticParams() {
  return [];
}

export default async function AdminAgentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AdminAgentDetailClient id={id} />;
}
