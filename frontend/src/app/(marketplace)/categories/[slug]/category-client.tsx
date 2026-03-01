"use client";

export default function CategoryClient({ slug }: { slug: string }) {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold">Category: {slug}</h1>
    </div>
  );
}
