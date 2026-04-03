// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_V1 } from "@/lib/constants";
import { getAuthHeaders } from "@/lib/auth-headers";
import type { Artifact } from "@/types/task";

/** A single chunk from the AG-UI streaming endpoint. */
export interface StreamChunk {
  type: "thinking" | "text" | "artifact" | "status" | "done" | "error";
  content?: string;
  artifact?: Artifact;
  artifacts?: Artifact[];
  metadata?: Record<string, unknown>;
}

interface UseTaskStreamReturn {
  /** Accumulated text chunks joined together */
  streamedText: string;
  /** All thinking chunks joined */
  thinkingText: string;
  /** Completed artifacts (from done event) */
  artifacts: Artifact[];
  /** Whether the stream is actively connected */
  isStreaming: boolean;
  /** Whether the stream has finished (done or error) */
  isDone: boolean;
  /** Error message if stream failed */
  error: string | null;
  /** Current status from status events */
  status: string | null;
}

/**
 * Hook that connects to the AG-UI task streaming endpoint via SSE.
 * Provides progressive text, thinking, artifacts, and status updates.
 *
 * Reuses the fetch-based SSE pattern from use-activity-feed.ts
 * (required because native EventSource doesn't support auth headers).
 */
export function useTaskStream(taskId: string | null): UseTaskStreamReturn {
  const [streamedText, setStreamedText] = useState("");
  const [thinkingText, setThinkingText] = useState("");
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const connect = useCallback(() => {
    if (!taskId) return;

    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("auth_token")
        : null;
    if (!token) return;

    // Cancel any existing connection
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsStreaming(true);
    setIsDone(false);
    setError(null);

    const url = `${API_V1}/tasks/${taskId}/stream`;

    (async () => {
      try {
        const res = await fetch(url, {
          headers: getAuthHeaders(token),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          throw new Error(`Stream response ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done: readerDone, value } = await reader.read();
          if (readerDone) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          let currentEventType = "";
          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEventType = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              const raw = line.slice(5).trim();
              if (!raw) continue;

              try {
                const chunk = JSON.parse(raw) as StreamChunk;
                const eventType = chunk.type || currentEventType;

                switch (eventType) {
                  case "text":
                    setStreamedText((prev) => prev + (chunk.content ?? ""));
                    break;

                  case "thinking":
                    setThinkingText((prev) => prev + (chunk.content ?? ""));
                    break;

                  case "artifact":
                    if (chunk.artifact) {
                      setArtifacts((prev) => [...prev, chunk.artifact!]);
                    }
                    break;

                  case "status":
                    setStatus(chunk.content ?? null);
                    break;

                  case "done":
                    if (chunk.artifacts && chunk.artifacts.length > 0) {
                      setArtifacts(chunk.artifacts);
                    }
                    setIsDone(true);
                    setIsStreaming(false);
                    return;

                  case "error":
                    setError(chunk.content ?? "Unknown streaming error");
                    setIsDone(true);
                    setIsStreaming(false);
                    return;
                }
              } catch {
                // ignore parse errors
              }
            }
          }
        }

        // Stream ended naturally
        setIsStreaming(false);
        if (!isDone) setIsDone(true);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setError((err as Error).message || "Stream connection failed");
        setIsStreaming(false);
        setIsDone(true);
      }
    })();

    return () => controller.abort();
  }, [taskId]);

  useEffect(() => {
    if (!taskId) return;
    const cleanup = connect();
    return () => {
      cleanup?.();
      abortRef.current?.abort();
    };
  }, [taskId, connect]);

  return {
    streamedText,
    thinkingText,
    artifacts,
    isStreaming,
    isDone,
    error,
    status,
  };
}
