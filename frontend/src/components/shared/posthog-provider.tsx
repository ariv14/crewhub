// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";

/**
 * PostHog analytics — loaded via external script tag (no npm dependency).
 * Tracks pageviews, sessions, and identifies authenticated users.
 *
 * Set NEXT_PUBLIC_POSTHOG_KEY env var (via POSTHOG_KEY GitHub secret) to enable.
 * Get your key from https://app.posthog.com → Project Settings.
 */

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY || "";
const POSTHOG_HOST =
  process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com";

declare global {
  interface Window {
    posthog?: {
      init: (
        key: string,
        config: Record<string, unknown>,
      ) => void;
      identify: (id: string, props?: Record<string, unknown>) => void;
      capture: (event: string, props?: Record<string, unknown>) => void;
      reset: () => void;
      _i?: unknown[];
      __SV?: number;
      push?: (...args: unknown[]) => void;
      people?: { toString: () => string };
    };
  }
}

export function PostHogProvider() {
  const { user } = useAuth();

  // Load PostHog via external script (safe — no innerHTML)
  useEffect(() => {
    if (!POSTHOG_KEY || typeof window === "undefined") return;
    if (window.posthog?.__SV) return; // already loaded

    // Initialize the posthog stub array
    const ph: Record<string, unknown> = {};
    window.posthog = ph as typeof window.posthog;
    (ph as { _i: unknown[] })._i = [];

    const initFn = (
      apiKey: string,
      config: Record<string, unknown>,
    ) => {
      (ph as { _i: unknown[] })._i.push([apiKey, config, "posthog"]);
    };
    (ph as { init: typeof initFn }).init = initFn;
    (ph as { __SV: number }).__SV = 1;

    // Stub common methods so calls before script loads are queued
    const methods = [
      "capture", "identify", "reset", "register", "get_distinct_id",
      "setPersonProperties", "group", "opt_in_capturing", "opt_out_capturing",
    ];
    for (const method of methods) {
      (ph as Record<string, (...args: unknown[]) => void>)[method] = (
        ...args: unknown[]
      ) => {
        (ph as { _i: unknown[] })._i.push([method, ...args]);
      };
    }

    // Load the real PostHog script
    const script = document.createElement("script");
    script.type = "text/javascript";
    script.async = true;
    script.crossOrigin = "anonymous";
    script.src = POSTHOG_HOST.replace(
      ".i.posthog.com",
      "-assets.i.posthog.com",
    ) + "/static/array.js";
    const firstScript = document.getElementsByTagName("script")[0];
    firstScript?.parentNode?.insertBefore(script, firstScript);

    // Initialize PostHog
    window.posthog!.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      person_profiles: "identified_only",
      capture_pageview: true,
      capture_pageleave: true,
      session_recording: {
        maskAllInputs: false,
        maskInputOptions: { password: true },
      },
    });
  }, []);

  // Identify user when they log in
  useEffect(() => {
    if (!POSTHOG_KEY || !window.posthog) return;

    if (user) {
      window.posthog.identify(user.id, {
        email: user.email,
        name: user.name,
      });
    }
  }, [user]);

  return null; // No UI — just side effects
}
