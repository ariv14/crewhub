// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { resetAnalyticsConsent } from "@/components/shared/posthog-provider";

/**
 * A small client component for the "Cookie Preferences" link in footers
 * and other server-rendered contexts. Resets analytics consent and
 * re-shows the consent banner.
 */
export function CookiePreferencesButton({ className }: { className?: string }) {
  return (
    <button
      type="button"
      onClick={() => resetAnalyticsConsent()}
      className={className}
    >
      Cookie Preferences
    </button>
  );
}
