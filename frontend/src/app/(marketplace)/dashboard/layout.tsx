// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { UserSidebar } from "@/components/layout/user-sidebar";
import { AuthGuard } from "@/components/shared/auth-guard";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex flex-1">
        <UserSidebar />
        <div className="flex-1 overflow-auto p-6">{children}</div>
      </div>
    </AuthGuard>
  );
}
