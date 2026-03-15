// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { API_V1 } from "@/lib/constants";
import AdminAgentDetailClient from "./admin-agent-detail-client";

export const dynamicParams = false;

export async function generateStaticParams() {
  const params: { id: string }[] = [{ id: "__fallback" }];
  try {
    const res = await fetch(`${API_V1}/agents/?per_page=100`);
    if (res.ok) {
      const data = await res.json();
      const agents: { id: string }[] = (data.agents ?? data).map(
        (a: { id: string }) => ({ id: a.id })
      );
      params.push(...agents);
    }
  } catch {}
  return params;
}

export default async function AdminAgentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AdminAgentDetailClient id={id} />;
}
