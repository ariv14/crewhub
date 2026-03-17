// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState, useEffect } from "react";
import { Loader2, Monitor } from "lucide-react";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

interface ExchangeCodeResponse {
  code: string;
  expires_in: number;
  builder_url: string;
}

export default function BuilderPage() {
  const { user } = useAuth();
  const [builderUrl, setBuilderUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    setIsMobile(window.innerWidth < 768);
  }, []);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    async function getBuilderAccess() {
      try {
        // Use builder.crewhubai.com proxy — same domain as parent,
        // so cookies work in iframe (third-party cookies blocked cross-origin)
        setBuilderUrl("https://builder.crewhubai.com");
      } catch {
        setError("Failed to load builder. Please try again.");
      } finally {
        setLoading(false);
      }
    }

    getBuilderAccess();
  }, [user]);

  if (isMobile) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
        <Monitor className="h-12 w-12 text-muted-foreground" />
        <h2 className="text-lg font-semibold">Desktop Recommended</h2>
        <p className="max-w-sm text-sm text-muted-foreground">
          The visual agent builder works best on a desktop or tablet screen.
          Please switch to a larger device.
        </p>
      </div>
    );
  }

  if (!user && !loading) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
        <h2 className="text-lg font-semibold">Sign in to Build Agents</h2>
        <p className="max-w-sm text-sm text-muted-foreground">
          Create AI agents visually with our drag-and-drop builder. Sign in to get started with 3 free agents.
        </p>
        <a
          href="/login?redirect=/dashboard/builder"
          className="rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground"
        >
          Sign In
        </a>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4">
        <p className="text-destructive">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      {/* Header bar */}
      <div className="flex items-center justify-between border-b bg-card px-4 py-2">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-semibold">CrewHub Agent Builder</h1>
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
            Beta
          </span>
        </div>
        <div className="flex items-center gap-4">
          <p className="hidden text-xs text-muted-foreground sm:block">
            Create a flow, then use our custom CrewHub components to build your agent
          </p>
          <span className="text-[10px] text-muted-foreground/50">
            Powered by Langflow
          </span>
        </div>
      </div>

      {/* Langflow iframe */}
      {builderUrl && (
        <iframe
          src={builderUrl}
          className="flex-1 border-0"
          allow="clipboard-read; clipboard-write"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
          title="CrewHub Agent Builder"
        />
      )}
    </div>
  );
}
