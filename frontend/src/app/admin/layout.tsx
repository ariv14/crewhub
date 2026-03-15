// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { TopNav } from "@/components/layout/top-nav";
import { AdminSidebar } from "@/components/layout/admin-sidebar";
import { AuthGuard } from "@/components/shared/auth-guard";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard requireAdmin>
      <div className="flex min-h-screen flex-col">
        <TopNav />
        <div className="flex flex-1">
          <AdminSidebar />
          <div className="flex-1 overflow-auto p-6">{children}</div>
        </div>
      </div>
    </AuthGuard>
  );
}
