"use client";

import { Activity, CheckCircle, XCircle } from "lucide-react";
import { useHealth } from "@/lib/hooks/use-health";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function AdminHealthPage() {
  const { data: health, isLoading } = useHealth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Platform Health</h1>
        <p className="mt-1 text-muted-foreground">
          Agent health and latency monitoring (auto-refreshes every 30s)
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-4 w-4" />
              API Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <span className="text-sm text-muted-foreground">Checking...</span>
            ) : health?.status === "ok" ? (
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-400" />
                <span className="font-medium text-green-400">Healthy</span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <XCircle className="h-5 w-5 text-red-400" />
                <span className="font-medium text-red-400">Unhealthy</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Registered Agents</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {health?.agents_registered ?? "—"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Active Agents</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {health?.agents_active ?? "—"}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Per-Agent Health</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Per-agent health cards with latency charts will be available once
            the backend health monitoring data is exposed via API.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
