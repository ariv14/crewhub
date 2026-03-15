// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import CategoryClient from "./category-client";

// All known category slugs — pre-render each at build time
const CATEGORY_SLUGS = [
  "general", "code", "data", "writing", "research",
  "design", "automation", "security", "finance", "support",
];

export const dynamicParams = false;

export async function generateStaticParams() {
  return CATEGORY_SLUGS.map((slug) => ({ slug }));
}

export default async function CategoryPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <CategoryClient slug={slug} />;
}
