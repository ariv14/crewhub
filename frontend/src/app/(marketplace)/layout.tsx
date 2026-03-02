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
        <TopNav />
        <main className="flex-1">{children}</main>
      </div>
    </AgentActivityProvider>
  );
}
