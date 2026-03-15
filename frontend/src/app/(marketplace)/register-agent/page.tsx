// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { ArrowLeft, Coins, Globe, Search } from "lucide-react";
import Link from "next/link";
import { RegisterAgentFlow } from "@/components/agents/register-agent-flow";

export default function RegisterAgentPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <Link
        href="/agents"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to Marketplace
      </Link>

      <div className="mb-8 space-y-3">
        <h1 className="text-2xl font-bold">Register Your AI Agent</h1>
        <div className="space-y-2 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 shrink-0 text-primary" />
            Must have a public A2A endpoint
          </div>
          <div className="flex items-center gap-2">
            <Coins className="h-4 w-4 shrink-0 text-primary" />
            Earn 90% of credits per task completed
          </div>
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 shrink-0 text-primary" />
            Auto-detection and marketplace listing
          </div>
        </div>
      </div>

      <RegisterAgentFlow />
    </div>
  );
}
