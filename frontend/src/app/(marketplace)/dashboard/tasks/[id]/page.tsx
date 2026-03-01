import TaskDetailClient from "./task-detail-client";

export const dynamicParams = false;

export async function generateStaticParams() {
  return [{ id: "__fallback" }];
}

export default async function TaskDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <TaskDetailClient id={id} />;
}
