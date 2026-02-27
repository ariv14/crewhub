import { TopNav } from "@/components/layout/top-nav";
import { AdminSidebar } from "@/components/layout/admin-sidebar";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <TopNav />
      <div className="flex flex-1">
        <AdminSidebar />
        <div className="flex-1 overflow-auto p-6">{children}</div>
      </div>
    </div>
  );
}
