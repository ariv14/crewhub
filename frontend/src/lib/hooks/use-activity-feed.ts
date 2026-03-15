// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_V1 } from "@/lib/constants";
import { getAuthHeaders } from "@/lib/auth-headers";

const STORAGE_KEY = "crewhub_activity_events";
const MAX_EVENTS = 50;

export interface ActivityEvent {
  type: string;
  [key: string]: unknown;
}

interface UseActivityFeedReturn {
  events: ActivityEvent[];
  connected: boolean;
}

function loadPersistedEvents(): ActivityEvent[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ActivityEvent[];
    // Filter out events older than 24 hours
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    return parsed.filter((e) => {
      const at = e.created_at as string | undefined;
      return at && new Date(at).getTime() > cutoff;
    });
  } catch {
    return [];
  }
}

function persistEvents(events: ActivityEvent[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events.slice(0, MAX_EVENTS)));
  } catch {
    // ignore storage errors
  }
}

/**
 * Connects to the SSE activity stream using fetch (supports Authorization
 * header). Persists events in localStorage so they survive page reloads.
 */
export function useActivityFeed(): UseActivityFeedReturn {
  const [events, setEvents] = useState<ActivityEvent[]>(loadPersistedEvents);
  const [connected, setConnected] = useState(false);
  const retryDelay = useRef(1000);
  const retryCount = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const pushEvent = useCallback((data: ActivityEvent) => {
    setEvents((prev) => {
      // Deduplicate by task_id/agent_id/transaction_id + type
      const key =
        (data.task_id as string) ??
        (data.agent_id as string) ??
        (data.transaction_id as string) ??
        "";
      const isDupe = key && prev.some(
        (e) =>
          e.type === data.type &&
          ((e.task_id as string) ?? (e.agent_id as string) ?? (e.transaction_id as string) ?? "") === key
      );
      if (isDupe) return prev;

      const updated = [data, ...prev].slice(0, MAX_EVENTS);
      persistEvents(updated);
      return updated;
    });
  }, []);

  const connect = useCallback(() => {
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("auth_token")
        : null;
    if (!token) return;

    // Cancel any in-flight connection
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const url = `${API_V1}/activity/stream`;

    // Use fetch-based SSE so we can send the Authorization header
    (async () => {
      try {
        const res = await fetch(url, {
          headers: getAuthHeaders(token),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          throw new Error(`SSE response ${res.status}`);
        }

        setConnected(true);
        retryDelay.current = 1000;
        retryCount.current = 0;

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // Keep the last incomplete line in the buffer
          buffer = lines.pop() ?? "";

          let currentEvent = "";
          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              const raw = line.slice(5).trim();
              if (raw) {
                try {
                  const data = JSON.parse(raw) as ActivityEvent;
                  if (currentEvent) data.type = currentEvent;
                  pushEvent(data);
                } catch {
                  // ignore parse errors
                }
              }
              currentEvent = "";
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        // Connection failed or closed — reconnect with backoff
      } finally {
        if (!controller.signal.aborted) {
          setConnected(false);
          retryCount.current += 1;
          // Stop retrying after 5 failures to avoid console spam
          if (retryCount.current > 5) return;
          const delay = Math.min(retryDelay.current, 30000);
          retryDelay.current = delay * 2;
          setTimeout(connect, delay);
        }
      }
    })();

    return () => {
      controller.abort();
      setConnected(false);
    };
  }, [pushEvent]);

  useEffect(() => {
    const cleanup = connect();
    return () => cleanup?.();
  }, [connect]);

  return { events, connected };
}
