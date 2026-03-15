// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { TopNav } from "@/components/layout/top-nav";
import { AgentActivityProvider } from "@/lib/hooks/use-agent-activity";

export default function MarketplaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AgentActivityProvider>
      <div className="flex min-h-screen flex-col">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-background focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:shadow-lg focus:ring-2 focus:ring-ring"
        >
          Skip to content
        </a>
        <TopNav />
        <main id="main-content" className="flex-1">{children}</main>
      </div>
    </AgentActivityProvider>
  );
}
