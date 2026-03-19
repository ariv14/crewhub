// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";

export interface Submission {
  id: string;
  user_id: string;
  langflow_flow_id: string;
  name: string;
  description: string | null;
  category: string | null;
  credits: number;
  tags: string[];
  status: string;
  reviewer_notes: string | null;
  agent_id: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface SubmissionList {
  submissions: Submission[];
  total: number;
}

export interface SubmissionCreate {
  langflow_flow_id: string;
  name: string;
  description?: string;
  category?: string;
  credits?: number;
  tags?: string[];
}

export async function createSubmission(data: SubmissionCreate): Promise<Submission> {
  return api.post("/builder/submissions", data);
}

export async function listSubmissions(page = 1, perPage = 20): Promise<SubmissionList> {
  return api.get(`/builder/submissions?page=${page}&per_page=${perPage}`);
}

export async function deleteSubmission(id: string): Promise<void> {
  return api.delete(`/builder/submissions/${id}`);
}

export interface SubmissionResubmit {
  langflow_flow_id?: string;
  name?: string;
  description?: string;
  category?: string;
  credits?: number;
  tags?: string[];
}

export async function resubmitSubmission(id: string, data: SubmissionResubmit): Promise<Submission> {
  return api.post(`/builder/submissions/${id}/resubmit`, data);
}
