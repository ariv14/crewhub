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
    if (!user) return;

    async function getBuilderAccess() {
      try {
        const data = await api.post<ExchangeCodeResponse>(
          "/builder/exchange-code"
        );
        setBuilderUrl(`${data.builder_url}?code=${data.code}`);
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
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-2">
          <h1 className="text-sm font-semibold">Agent Builder</h1>
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
            Beta
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Drag components from the left sidebar to build your agent
        </p>
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
