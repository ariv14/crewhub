// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useEffect, useState } from "react";
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

const CONSENT_KEY = "analytics_consent";

function getConsent(): boolean | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem(CONSENT_KEY);
  if (v === "true") return true;
  if (v === "false") return false;
  return null;
}

function isDNT(): boolean {
  if (typeof navigator === "undefined") return false;
  return navigator.doNotTrack === "1" || (navigator as unknown as Record<string, string>).globalPrivacyControl === "1";
}

export function PostHogProvider() {
  const { user } = useAuth();
  const [consent, setConsent] = useState<boolean | null>(() => getConsent());
  const [showBanner, setShowBanner] = useState(false);

  // Show banner if no consent decision yet and DNT is not set
  useEffect(() => {
    if (consent === null && !isDNT()) {
      setShowBanner(true);
    }
  }, [consent]);

  // Load PostHog only after consent is given (and DNT is not set)
  useEffect(() => {
    if (!POSTHOG_KEY || typeof window === "undefined") return;
    if (consent !== true || isDNT()) return;
    if (window.posthog?.__SV) return;

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

    window.posthog!.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      person_profiles: "identified_only",
      capture_pageview: true,
      capture_pageleave: true,
      session_recording: {
        maskAllInputs: true,
      },
    });
  }, [consent]);

  // Identify user only after consent
  useEffect(() => {
    if (!POSTHOG_KEY || !window.posthog || consent !== true) return;
    if (user) {
      window.posthog.identify(user.id, {
        email: user.email,
        name: user.name,
      });
    }
  }, [user, consent]);

  function handleAccept() {
    localStorage.setItem(CONSENT_KEY, "true");
    setConsent(true);
    setShowBanner(false);
  }

  function handleDecline() {
    localStorage.setItem(CONSENT_KEY, "false");
    setConsent(false);
    setShowBanner(false);
  }

  if (!showBanner) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-[100] border-t bg-card/95 px-4 py-3 shadow-lg backdrop-blur-sm sm:bottom-4 sm:left-4 sm:right-auto sm:max-w-sm sm:rounded-xl sm:border">
      <p className="text-sm text-muted-foreground">
        We use cookies for analytics to improve the platform.{" "}
        <a href="/privacy" className="text-primary hover:underline">Privacy Policy</a>
      </p>
      <div className="mt-2 flex gap-2">
        <button
          onClick={handleAccept}
          className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground"
        >
          Accept
        </button>
        <button
          onClick={handleDecline}
          className="rounded-md border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          Decline
        </button>
      </div>
    </div>
  );
}
