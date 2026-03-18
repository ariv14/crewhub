// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useEffect } from "react";

/**
 * Team Mode has been merged into Workflows.
 * This page redirects to the workflow creation page.
 */
export default function TeamRedirect() {
  useEffect(() => {
    window.location.href = "/dashboard/workflows/new";
  }, []);

  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <p className="text-muted-foreground">Redirecting to Workflows...</p>
    </div>
  );
}
