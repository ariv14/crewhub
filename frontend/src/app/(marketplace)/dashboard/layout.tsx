import { UserSidebar } from "@/components/layout/user-sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-1">
      <UserSidebar />
      <div className="flex-1 overflow-auto p-6">{children}</div>
    </div>
  );
}
