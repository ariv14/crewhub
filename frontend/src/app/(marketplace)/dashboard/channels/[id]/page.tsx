// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import ChannelDetailClient from "./channel-detail-client";

export async function generateStaticParams() {
  return [{ id: "__fallback" }];
}

export default async function ChannelDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ChannelDetailClient channelId={id} />;
}
