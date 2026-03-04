"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { API_V1 } from "@/lib/constants";

type Intensity = "low" | "medium" | "high";

interface AgentActivity {
  lastEventType: string;
  timestamp: number;
  eventCount: number;
}

interface AgentActivityContextValue {
  getActivity: (agentId: string) => {
    isActive: boolean;
    intensity: Intensity;
    lastEventType: string;
  } | null;
  connected: boolean;
}

const AgentActivityContext = createContext<AgentActivityContextValue>({
  getActivity: () => null,
  connected: false,
});

export function useAgentActivity() {
  return useContext(AgentActivityContext);
}

const ACTIVE_WINDOW_MS = 10_000;
const INTENSITY_WINDOW_MS = 30_000;

function computeIntensity(count: number): Intensity {
  if (count >= 5) return "high";
  if (count >= 2) return "medium";
  return "low";
}

export function AgentActivityProvider({ children }: { children: ReactNode }) {
  const activityMap = useRef(new Map<string, AgentActivity>());
  const [, setTick] = useState(0);
  const [connected, setConnected] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const retryCount = useRef(0);
  const retryDelay = useRef(1000);

  const processEvent = useCallback(
    (agentId: string, eventType: string) => {
      const now = Date.now();
      const existing = activityMap.current.get(agentId);

      if (existing && now - existing.timestamp < INTENSITY_WINDOW_MS) {
        existing.lastEventType = eventType;
        existing.timestamp = now;
        existing.eventCount += 1;
      } else {
        activityMap.current.set(agentId, {
          lastEventType: eventType,
          timestamp: now,
          eventCount: 1,
        });
      }
      setTick((t) => t + 1);
    },
    [],
  );

  const handleSSEEvent = useCallback(
    (data: Record<string, unknown>) => {
      const eventType = (data.type as string) ?? "";
      const agentId =
        (data.provider_agent_id as string) ?? (data.agent_id as string);
      if (agentId) {
        processEvent(agentId, eventType);
      }
    },
    [processEvent],
  );

  const connect = useCallback(() => {
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("auth_token")
        : null;
    if (!token) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    (async () => {
      try {
        const res = await fetch(`${API_V1}/activity/stream`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });

        if (!res.ok || !res.body) throw new Error(`SSE ${res.status}`);

        setConnected(true);
        retryCount.current = 0;
        retryDelay.current = 1000;

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          let currentEvent = "";
          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              const raw = line.slice(5).trim();
              if (raw) {
                try {
                  const data = JSON.parse(raw) as Record<string, unknown>;
                  if (currentEvent) data.type = currentEvent;
                  handleSSEEvent(data);
                } catch {
                  /* ignore parse errors */
                }
              }
              currentEvent = "";
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return;
      } finally {
        if (!controller.signal.aborted) {
          setConnected(false);
          retryCount.current += 1;
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
  }, [handleSSEEvent]);

  useEffect(() => {
    const cleanup = connect();
    return () => cleanup?.();
  }, [connect]);

  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      let changed = false;
      for (const [id, entry] of activityMap.current) {
        if (now - entry.timestamp > INTENSITY_WINDOW_MS) {
          activityMap.current.delete(id);
          changed = true;
        }
      }
      if (changed) setTick((t) => t + 1);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const getActivity = useCallback(
    (agentId: string) => {
      const entry = activityMap.current.get(agentId);
      if (!entry) return null;

      const age = Date.now() - entry.timestamp;
      if (age > ACTIVE_WINDOW_MS) return null;

      return {
        isActive: true,
        intensity: computeIntensity(entry.eventCount),
        lastEventType: entry.lastEventType,
      };
    },
    [],
  );

  return (
    <AgentActivityContext.Provider value={{ getActivity, connected }}>
      {children}
    </AgentActivityContext.Provider>
  );
}
