"use client";

import { useParams } from "next/navigation";

export default function CategoryClient({ slug: serverSlug }: { slug: string }) {
  const params = useParams<{ slug: string }>();
  const slug = params.slug && params.slug !== "_" ? params.slug : serverSlug;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold">Category: {slug}</h1>
    </div>
  );
}
