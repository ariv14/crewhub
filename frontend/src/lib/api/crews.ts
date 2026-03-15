// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";
import type {
  Crew,
  CrewCreate,
  CrewListResponse,
  CrewRunRequest,
  CrewRunResponse,
  CrewUpdate,
} from "@/types/crew";

export async function listMyCrews(): Promise<CrewListResponse> {
  return api.get("/crews/");
}

export async function listPublicCrews(): Promise<CrewListResponse> {
  return api.get("/crews/public");
}

export async function getCrew(id: string): Promise<Crew> {
  return api.get(`/crews/${id}`);
}

export async function createCrew(data: CrewCreate): Promise<Crew> {
  return api.post("/crews/", data);
}

export async function updateCrew(id: string, data: CrewUpdate): Promise<Crew> {
  return api.put(`/crews/${id}`, data);
}

export async function deleteCrew(id: string): Promise<void> {
  return api.delete(`/crews/${id}`);
}

export async function runCrew(
  id: string,
  data: CrewRunRequest
): Promise<CrewRunResponse> {
  return api.post(`/crews/${id}/run`, data);
}

export async function cloneCrew(id: string): Promise<Crew> {
  return api.post(`/crews/${id}/clone`, {});
}
