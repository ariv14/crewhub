// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import CrewDetailClient from "./crew-detail-client";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ id: "__fallback" }];
}

export default async function CrewDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <CrewDetailClient id={id} />;
}
