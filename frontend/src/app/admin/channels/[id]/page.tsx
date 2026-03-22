// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import AdminChannelDetailClient from "./admin-channel-detail-client";

export default function AdminChannelDetailPage({ params }: { params: { id: string } }) {
  return <AdminChannelDetailClient channelId={params.id} />;
}
