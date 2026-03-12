export const dynamicParams = false;

export function generateStaticParams() {
  return [{ id: "__fallback" }];
}

export default async function WorkflowDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  // Dynamic import to keep this a server component shell
  const { WorkflowDetailClient } = await import("./workflow-detail-client");
  return <WorkflowDetailClient serverId={id} />;
}
