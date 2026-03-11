"use client";

import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export function PricingCTA() {
  const { user } = useAuth();
  return (
    <Link
      href={user ? "/dashboard/credits" : "/register"}
      className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
    >
      {user ? "Buy Credits" : "Get Started Free"}
      <ArrowRight className="h-4 w-4" />
    </Link>
  );
}
