import AdminAgentDetailClient from "./admin-agent-detail-client";

export const dynamicParams = false;

export async function generateStaticParams() {
  return [{ id: "_" }];
}

export default async function AdminAgentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AdminAgentDetailClient id={id} />;
}
