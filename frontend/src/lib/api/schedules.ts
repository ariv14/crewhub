import { api } from "../api-client";
import type {
  Schedule,
  ScheduleCreate,
  ScheduleListResponse,
  ScheduleUpdate,
} from "@/types/schedule";

export async function listMySchedules(): Promise<ScheduleListResponse> {
  return api.get("/schedules/");
}

export async function getSchedule(id: string): Promise<Schedule> {
  return api.get(`/schedules/${id}`);
}

export async function createSchedule(data: ScheduleCreate): Promise<Schedule> {
  return api.post("/schedules/", data);
}

export async function updateSchedule(
  id: string,
  data: ScheduleUpdate
): Promise<Schedule> {
  return api.put(`/schedules/${id}`, data);
}

export async function deleteSchedule(id: string): Promise<void> {
  return api.delete(`/schedules/${id}`);
}

export async function pauseSchedule(id: string): Promise<Schedule> {
  return api.post(`/schedules/${id}/pause`, {});
}

export async function resumeSchedule(id: string): Promise<Schedule> {
  return api.post(`/schedules/${id}/resume`, {});
}
