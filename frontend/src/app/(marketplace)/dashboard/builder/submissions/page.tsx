// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useEffect } from "react";
import { Clock, CheckCircle2, XCircle, Loader2, Trash2, ExternalLink, RotateCcw } from "lucide-react";
import { useSubmissions, useDeleteSubmission, useResubmitSubmission } from "@/lib/hooks/use-builder";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

const STATUS_CONFIG: Record<string, { icon: typeof CheckCircle2; variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
  pending_review: { icon: Clock, variant: "outline", label: "Pending Review" },
  approved: { icon: CheckCircle2, variant: "default", label: "Approved" },
  rejected: { icon: XCircle, variant: "destructive", label: "Rejected" },
  revoked: { icon: XCircle, variant: "secondary", label: "Revoked" },
};

export default function SubmissionsPage() {
  const { data, isLoading } = useSubmissions();
  const deleteMutation = useDeleteSubmission();
  const resubmitMutation = useResubmitSubmission();

  // Notify on status changes (localStorage diff)
  useEffect(() => {
    if (!data) return;
    const stored = JSON.parse(localStorage.getItem("submission_statuses") || "{}");
    for (const sub of data.submissions) {
      const prev = stored[sub.id];
      if (prev === "pending_review" && sub.status === "approved") {
        toast.success(`"${sub.name}" was approved and is now live!`);
      } else if (prev === "pending_review" && sub.status === "rejected") {
        toast.error(`"${sub.name}" was rejected. See reviewer notes below.`);
      }
    }
    const next: Record<string, string> = {};
    for (const sub of data.submissions) next[sub.id] = sub.status;
    localStorage.setItem("submission_statuses", JSON.stringify(next));
  }, [data]);

  async function handleDelete(id: string) {
    try {
      await deleteMutation.mutateAsync(id);
      toast.success("Submission deleted");
    } catch {
      toast.error("Failed to delete submission");
    }
  }

  async function handleResubmit(id: string) {
    try {
      await resubmitMutation.mutateAsync({ id, data: {} });
      toast.success("Resubmitted for review!");
    } catch {
      toast.error("Failed to resubmit");
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  const submissions = data?.submissions ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold">My Agent Submissions</h1>
          <p className="text-sm text-muted-foreground">
            Track the status of agents you&apos;ve submitted for marketplace review.
          </p>
        </div>
        <a href="/dashboard/builder">
          <Button size="sm">Build New Agent</Button>
        </a>
      </div>

      {submissions.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-sm text-muted-foreground">
              No submissions yet. Build an agent and publish it to the marketplace!
            </p>
            <a href="/dashboard/builder" className="mt-4">
              <Button size="sm">Open Builder</Button>
            </a>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {submissions.map((sub) => {
            const config = STATUS_CONFIG[sub.status] ?? STATUS_CONFIG.pending_review;
            const StatusIcon = config.icon;

            return (
              <Card key={sub.id}>
                <CardContent className="flex items-center justify-between py-4">
                  <div className="flex items-center gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold">{sub.name}</h3>
                        <Badge variant={config.variant} className="gap-1 text-[10px]">
                          <StatusIcon className="h-3 w-3" />
                          {config.label}
                        </Badge>
                      </div>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {sub.category} &bull; {sub.credits} credits &bull;{" "}
                        {new Date(sub.created_at).toLocaleDateString()}
                      </p>
                      {sub.reviewer_notes && (
                        <p className="mt-1 text-xs text-destructive">
                          Reviewer: {sub.reviewer_notes}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {sub.agent_id && (
                      <a href={`/agents/${sub.agent_id}/`}>
                        <Button variant="outline" size="sm" className="gap-1">
                          <ExternalLink className="h-3 w-3" />
                          View Agent
                        </Button>
                      </a>
                    )}
                    {sub.status === "rejected" && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-1"
                        onClick={() => handleResubmit(sub.id)}
                        disabled={resubmitMutation.isPending}
                      >
                        <RotateCcw className="h-3 w-3" />
                        Resubmit
                      </Button>
                    )}
                    {sub.status !== "approved" && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(sub.id)}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4 text-muted-foreground" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
