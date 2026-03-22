// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import AdminChannelDetailClient from "./admin-channel-detail-client";

export const dynamicParams = false;

export async function generateStaticParams() {
  return [{ id: "__fallback" }];
}

export default async function AdminChannelDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AdminChannelDetailClient channelId={id} />;
}
