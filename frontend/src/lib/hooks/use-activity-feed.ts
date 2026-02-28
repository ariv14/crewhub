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

export function useActivityFeed(): UseActivityFeedReturn {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const retryDelay = useRef(1000);

  const connect = useCallback(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    if (!token) return;

    const url = `${API_V1}/activity/stream?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);

    es.onopen = () => {
      setConnected(true);
      retryDelay.current = 1000;
    };

    const handleEvent = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as ActivityEvent;
        setEvents((prev) => [data, ...prev].slice(0, 20));
      } catch {
        // ignore parse errors
      }
    };

    // Listen for all known event types
    const eventTypes = [
      "task_created",
      "task_completed",
      "task_failed",
      "agent_registered",
      "credit_transaction",
    ];
    for (const type of eventTypes) {
      es.addEventListener(type, handleEvent);
    }

    es.onerror = () => {
      setConnected(false);
      es.close();
      // Exponential backoff reconnect
      const delay = Math.min(retryDelay.current, 30000);
      retryDelay.current = delay * 2;
      setTimeout(connect, delay);
    };

    return () => {
      es.close();
      setConnected(false);
    };
  }, []);

  useEffect(() => {
    const cleanup = connect();
    return () => cleanup?.();
  }, [connect]);

  return { events, connected };
}
