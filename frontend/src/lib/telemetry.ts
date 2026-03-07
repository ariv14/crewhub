import { api } from "./api-client";

interface TelemetryEvent {
  name: string;
  properties?: Record<string, unknown>;
}

let _buffer: TelemetryEvent[] = [];
let _timer: ReturnType<typeof setTimeout> | null = null;

const FLUSH_INTERVAL = 10_000; // 10 seconds
const MAX_BUFFER = 50;

function scheduleFlush() {
  if (_timer) return;
  _timer = setTimeout(flush, FLUSH_INTERVAL);
}

async function flush() {
  _timer = null;
  if (_buffer.length === 0) return;

  const events = [..._buffer];
  _buffer = [];

  try {
    await api.post("/telemetry/events", { events });
  } catch {
    // Best-effort — don't retry failed telemetry
  }
}

export function trackEvent(name: string, properties?: Record<string, unknown>) {
  _buffer.push({ name, properties: { ...properties, ts: Date.now() } });

  if (_buffer.length >= MAX_BUFFER) {
    flush();
  } else {
    scheduleFlush();
  }
}

// Flush on page unload
if (typeof window !== "undefined") {
  window.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      flush();
    }
  });
}
