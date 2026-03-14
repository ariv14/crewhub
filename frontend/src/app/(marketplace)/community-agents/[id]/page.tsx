import { Suspense } from "react";
import CommunityAgentDetailClient from "./community-agent-detail-client";

export const dynamicParams = false;

export async function generateStaticParams() {
  return [{ id: "__fallback" }];
}

export default async function CommunityAgentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <Suspense>
      <CommunityAgentDetailClient id={id} />
    </Suspense>
  );
}
