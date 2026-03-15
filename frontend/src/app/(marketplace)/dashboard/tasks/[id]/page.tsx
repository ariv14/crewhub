// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { API_V1 } from "@/lib/constants";
import TaskDetailClient from "./task-detail-client";

export async function generateStaticParams() {
  try {
    const res = await fetch(`${API_V1}/tasks/?per_page=100`);
    if (res.ok) {
      const data = await res.json();
      const tasks: { id: string }[] = (data.tasks ?? data).map(
        (t: { id: string }) => ({ id: t.id })
      );
      return tasks;
    }
  } catch {}
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
