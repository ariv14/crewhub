// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useEffect } from "react";

interface Shortcut {
  keys: string[];
  action: () => void;
  description: string;
}

export const SHORTCUTS: Omit<Shortcut, "action">[] = [
  { keys: ["g", "d"], description: "Go to Dashboard" },
  { keys: ["g", "a"], description: "Go to Agents" },
  { keys: ["g", "t"], description: "Go to Tasks" },
  { keys: ["g", "w"], description: "Go to Workflows" },
  { keys: ["n", "t"], description: "New Task" },
  { keys: ["?"], description: "Show shortcuts" },
];

export function useHotkeys() {
  useEffect(() => {
    let buffer: string[] = [];
    let timer: ReturnType<typeof setTimeout>;

    function handleKeydown(e: KeyboardEvent) {
      // Skip if user is typing in an input/textarea
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      clearTimeout(timer);
      buffer.push(e.key.toLowerCase());

      // Check for matches
      const seq = buffer.join("");

      if (seq === "gd") {
        window.location.href = "/dashboard";
        buffer = [];
        return;
      }
      if (seq === "ga") {
        window.location.href = "/agents";
        buffer = [];
        return;
      }
      if (seq === "gt") {
        window.location.href = "/dashboard/tasks";
        buffer = [];
        return;
      }
      if (seq === "gw") {
        window.location.href = "/dashboard/workflows";
        buffer = [];
        return;
      }
      if (seq === "nt") {
        window.location.href = "/dashboard/tasks/new";
        buffer = [];
        return;
      }
      if (e.key === "?" && buffer.length === 1) {
        // Toggle command palette via Cmd+K simulation
        document.dispatchEvent(
          new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true })
        );
        buffer = [];
        return;
      }

      // Reset buffer after 800ms of inactivity
      timer = setTimeout(() => {
        buffer = [];
      }, 800);
    }

    document.addEventListener("keydown", handleKeydown);
    return () => {
      document.removeEventListener("keydown", handleKeydown);
      clearTimeout(timer);
    };
  }, []);
}
