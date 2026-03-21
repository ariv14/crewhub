// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { Suspense, useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

interface AuthGuardProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

const LoadingSpinner = (
  <div className="flex min-h-[50vh] items-center justify-center">
    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
  </div>
);

function AuthGuardInner({ children, requireAdmin = false }: AuthGuardProps) {
  const { user, loading, isAdmin } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (loading) return;

    if (!user) {
      const search = searchParams.toString();
      const fullPath = search ? `${pathname}?${search}` : pathname;
      const params = new URLSearchParams();
      params.set("redirect", fullPath);
      router.replace(`/login?${params.toString()}`);
      return;
    }

    if (requireAdmin && !isAdmin) {
      router.replace("/dashboard");
    }
  }, [user, loading, isAdmin, requireAdmin, router, pathname, searchParams]);

  if (loading) return LoadingSpinner;
  if (!user) return null;
  if (requireAdmin && !isAdmin) return null;

  return <>{children}</>;
}

export function AuthGuard(props: AuthGuardProps) {
  return (
    <Suspense fallback={LoadingSpinner}>
      <AuthGuardInner {...props} />
    </Suspense>
  );
}
