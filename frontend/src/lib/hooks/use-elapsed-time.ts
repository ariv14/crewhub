// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useState, useEffect } from "react";

export function useElapsedTime(startTime: string | null, active: boolean, endTime?: string | null) {
  const [elapsed, setElapsed] = useState("");

  useEffect(() => {
    if (!startTime || !active) {
      if (startTime && !active) {
        const end = endTime ? new Date(endTime).getTime() : Date.now();
        setElapsed(formatElapsed(end - new Date(startTime).getTime()));
      }
      return;
    }

    function tick() {
      const ms = Date.now() - new Date(startTime!).getTime();
      setElapsed(formatElapsed(ms));
    }

    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [startTime, active, endTime]);

  return elapsed;
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) return `${minutes}m ${seconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}
