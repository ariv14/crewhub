// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import { Clock, CheckCircle2, XCircle, ExternalLink, Eye, Ban, Send } from "lucide-react";
import { formatRelativeTime } from "@/lib/utils";
import {
  useAdminSubmissions,
  useApproveSubmission,
  useRejectSubmission,
  useRevokeSubmission,
} from "@/lib/hooks/use-admin-submissions";
import type { Submission } from "@/lib/api/builder";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Textarea } from "@/components/ui/textarea";

const STATUS_CONFIG: Record<string, { variant: "outline" | "default" | "destructive" | "secondary"; icon: typeof Clock }> = {
  pending_review: { variant: "outline", icon: Clock },
  approved: { variant: "default", icon: CheckCircle2 },
  rejected: { variant: "destructive", icon: XCircle },
  revoked: { variant: "secondary", icon: XCircle },
};

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending_review;
  const Icon = config.icon;
  return (
    <Badge variant={config.variant} className="gap-1 text-xs capitalize">
      <Icon className="h-3 w-3" />
      {status.replace("_", " ")}
    </Badge>
  );
}

function SubmissionCard({
  submission,
  onApprove,
  onReject,
  onRevoke,
}: {
  submission: Submission;
  onApprove: (id: string) => void;
  onReject: (id: string, notes: string) => void;
  onRevoke: (id: string) => void;
}) {
  const [rejectNotes, setRejectNotes] = useState("");

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{submission.name}</CardTitle>
          <StatusBadge status={submission.status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground">
          <span>Submitted by: <span className="font-mono text-xs">{submission.user_id}</span></span>
          <span>{formatRelativeTime(submission.created_at)}</span>
        </div>

        <div className="flex flex-wrap gap-2">
          {submission.category && (
            <Badge variant="secondary" className="text-xs">{submission.category}</Badge>
          )}
          <Badge variant="outline" className="text-xs">{submission.credits} credits</Badge>
          {submission.tags?.map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
          ))}
        </div>

        {submission.description && (
          <p className="line-clamp-2 text-muted-foreground">{submission.description}</p>
        )}

        <div className="text-muted-foreground">
          Flow ID: <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">{submission.langflow_flow_id}</code>
        </div>

        {/* Reviewer notes for rejected submissions */}
        {submission.status === "rejected" && submission.reviewer_notes && (
          <p className="text-sm italic text-muted-foreground">
            Rejection notes: {submission.reviewer_notes}
          </p>
        )}

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2 pt-1">
          {submission.status === "pending_review" && (
            <>
              <Button variant="outline" size="sm" asChild>
                <a href="https://builder.crewhubai.com" target="_blank" rel="noopener noreferrer">
                  Test in Langflow <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              </Button>

              {/* Reject dialog */}
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="outline" size="sm" className="text-destructive">
                    <Ban className="mr-1 h-3 w-3" />
                    Reject
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Reject Submission</AlertDialogTitle>
                    <AlertDialogDescription>
                      Provide notes explaining why this submission is being rejected. This will be visible to the builder.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <Textarea
                    placeholder="Rejection notes (required)..."
                    value={rejectNotes}
                    onChange={(e) => setRejectNotes(e.target.value)}
                    rows={3}
                  />
                  <AlertDialogFooter>
                    <AlertDialogCancel onClick={() => setRejectNotes("")}>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      disabled={!rejectNotes.trim()}
                      onClick={() => {
                        onReject(submission.id, rejectNotes.trim());
                        setRejectNotes("");
                      }}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                      Reject
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>

              {/* Approve dialog */}
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button size="sm">
                    <CheckCircle2 className="mr-1 h-3 w-3" />
                    Approve
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Approve Submission</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will create a new agent from the builder flow and make it available on the marketplace. Continue?
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={() => onApprove(submission.id)}>
                      Approve
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </>
          )}

          {submission.status === "approved" && (
            <>
              {submission.agent_id && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    window.location.href = `/agents/${submission.agent_id}/`;
                  }}
                >
                  <Eye className="mr-1 h-3 w-3" />
                  View Agent
                </Button>
              )}

              {/* Revoke dialog */}
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="outline" size="sm" className="text-destructive">
                    <Ban className="mr-1 h-3 w-3" />
                    Revoke
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Revoke Submission</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will revoke the approved submission and deactivate the associated agent. This action cannot be undone. Continue?
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={() => onRevoke(submission.id)}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                      Revoke
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdminSubmissionsPage() {
  const [status, setStatus] = useState("pending_review");
  const [page, setPage] = useState(1);
  const perPage = 20;

  const { data, isLoading } = useAdminSubmissions(status, page, perPage);
  const approve = useApproveSubmission();
  const reject = useRejectSubmission();
  const revoke = useRevokeSubmission();

  const submissions = data?.submissions ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Agent Submissions</h1>
        <p className="mt-1 text-muted-foreground">
          Review and approve agent submissions from the no-code builder
        </p>
      </div>

      <div className="flex items-center gap-4">
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="pending_review">Pending Review</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
            <SelectItem value="revoked">Revoked</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground">
          {total} submission{total !== 1 ? "s" : ""}
        </span>
      </div>

      {isLoading ? (
        <div className="py-12 text-center text-muted-foreground">Loading submissions...</div>
      ) : submissions.length === 0 ? (
        <div className="py-12 text-center text-muted-foreground">
          No {status.replace("_", " ")} submissions found.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {submissions.map((s) => (
            <SubmissionCard
              key={s.id}
              submission={s}
              onApprove={(id) => approve.mutate(id)}
              onReject={(id, notes) => reject.mutate({ id, notes })}
              onRevoke={(id) => revoke.mutate(id)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
