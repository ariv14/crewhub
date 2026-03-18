// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";
import type {
  Channel,
  ChannelListResponse,
  ChannelCreate,
  ChannelUpdate,
  ChannelAnalytics,
  ChannelTestResult,
} from "@/types/channel";

export async function getChannels(): Promise<ChannelListResponse> {
  return api.get<ChannelListResponse>("/channels/");
}

export async function getChannel(id: string): Promise<Channel> {
  return api.get<Channel>(`/channels/${id}`);
}

export async function createChannel(data: ChannelCreate): Promise<Channel> {
  return api.post<Channel>("/channels/", data);
}

export async function updateChannel(id: string, data: ChannelUpdate): Promise<Channel> {
  return api.patch<Channel>(`/channels/${id}`, data);
}

export async function deleteChannel(id: string): Promise<void> {
  return api.delete(`/channels/${id}`);
}

export async function rotateChannelToken(id: string, credentials: Record<string, string>): Promise<Channel> {
  return api.post<Channel>(`/channels/${id}/rotate-token`, credentials);
}

export async function getChannelAnalytics(id: string, days: number = 7): Promise<ChannelAnalytics> {
  return api.get<ChannelAnalytics>(`/channels/${id}/analytics?days=${days}`);
}

export async function testChannel(id: string): Promise<ChannelTestResult> {
  return api.post<ChannelTestResult>(`/channels/${id}/test`);
}
