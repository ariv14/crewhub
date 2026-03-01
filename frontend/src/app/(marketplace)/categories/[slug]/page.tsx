import CategoryClient from "./category-client";

export const dynamicParams = false;

export async function generateStaticParams() {
  return [{ slug: "_" }];
}

export default async function CategoryPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <CategoryClient slug={slug} />;
}
