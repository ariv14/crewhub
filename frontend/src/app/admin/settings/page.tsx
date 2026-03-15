// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { Settings } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const CONFIG_ITEMS = [
  { label: "Platform Fee Rate", value: "10%", description: "Commission on each task" },
  { label: "New User Bonus", value: "250 credits", description: "Signup bonus" },
  { label: "Health Check Interval", value: "60s", description: "Agent health poll interval" },
  { label: "Rate Limit", value: "100 req/60s", description: "Per-user API rate limit" },
  { label: "x402 Receipt Timeout", value: "10 min", description: "Time to submit payment receipt" },
];

export default function AdminSettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Platform Settings</h1>
        <p className="mt-1 text-muted-foreground">
          Current platform configuration (read-only)
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Settings className="h-4 w-4" />
            Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="divide-y">
            {CONFIG_ITEMS.map((item) => (
              <div key={item.label} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-medium">{item.label}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.description}
                  </p>
                </div>
                <span className="font-mono text-sm">{item.value}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
