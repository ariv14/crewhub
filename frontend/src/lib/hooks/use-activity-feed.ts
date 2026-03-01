"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_V1 } from "@/lib/constants";

export interface ActivityEvent {
  type: string;
  [key: string]: unknown;
}

interface UseActivityFeedReturn {
  events: ActivityEvent[];
  connected: boolean;
}

/**
 * Connects to the SSE activity stream using fetch (supports Authorization
 * header). Falls back to EventSource with query-param token if fetch-based
 * SSE is unavailable.
 */
export function useActivityFeed(): UseActivityFeedReturn {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const retryDelay = useRef(1000);
  const retryCount = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const pushEvent = useCallback((data: ActivityEvent) => {
    setEvents((prev) => [data, ...prev].slice(0, 20));
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
          headers: { Authorization: `Bearer ${token}` },
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
