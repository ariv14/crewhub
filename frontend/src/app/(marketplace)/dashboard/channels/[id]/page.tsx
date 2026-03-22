// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import ChannelDetailClient from "./channel-detail-client";

export default function ChannelDetailPage({ params }: { params: { id: string } }) {
  return <ChannelDetailClient channelId={params.id} />;
}
