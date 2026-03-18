// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";
import type { Submission, SubmissionList } from "./builder";

export async function listAdminSubmissions(
  status: string = "pending_review",
  page: number = 1,
  perPage: number = 20
): Promise<SubmissionList> {
  return api.get<SubmissionList>(
    `/admin/submissions/?status=${status}&page=${page}&per_page=${perPage}`
  );
}

export async function approveSubmission(id: string): Promise<{ status: string; agent_id: string; submission_id: string }> {
  return api.post(`/admin/submissions/${id}/approve`);
}

export async function rejectSubmission(id: string, notes: string): Promise<{ status: string; submission_id: string }> {
  return api.post(`/admin/submissions/${id}/reject?notes=${encodeURIComponent(notes)}`);
}

export async function revokeSubmission(id: string): Promise<{ status: string; submission_id: string }> {
  return api.post(`/admin/submissions/${id}/revoke`);
}
