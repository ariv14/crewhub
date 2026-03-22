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
  ChannelContactList,
  ChannelMessageList,
  AdminChannel,
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

export async function getContacts(channelId: string, limit = 50, offset = 0): Promise<ChannelContactList> {
  return api.get(`/channels/${channelId}/contacts?limit=${limit}&offset=${offset}`);
}

export async function getContactMessages(channelId: string, userHash: string, cursor?: string): Promise<ChannelMessageList> {
  const params = cursor ? `?cursor=${cursor}` : "";
  return api.get(`/channels/${channelId}/contacts/${userHash}/messages${params}`);
}

export async function getChannelMessages(channelId: string, direction?: string, cursor?: string): Promise<ChannelMessageList> {
  const params = new URLSearchParams();
  if (direction) params.set("direction", direction);
  if (cursor) params.set("cursor", cursor);
  const qs = params.toString();
  return api.get(`/channels/${channelId}/messages${qs ? `?${qs}` : ""}`);
}

export async function blockContact(channelId: string, userHash: string, reason?: string): Promise<void> {
  return api.post(`/channels/${channelId}/contacts/${userHash}/block`, { reason: reason || "" });
}

export async function unblockContact(channelId: string, userHash: string): Promise<void> {
  return api.delete(`/channels/${channelId}/contacts/${userHash}/block`);
}

export async function deleteContactData(channelId: string, userHash: string): Promise<{ deleted_messages: number }> {
  return api.delete(`/channels/${channelId}/contacts/${userHash}/messages`);
}

// Admin
export async function getAdminChannels(): Promise<{ channels: AdminChannel[]; total: number }> {
  return api.get("/admin/channels/");
}

export async function getAdminChannel(channelId: string): Promise<AdminChannel> {
  return api.get(`/admin/channels/${channelId}`);
}

export async function getAdminChannelMessages(channelId: string, justification: string, cursor?: string): Promise<ChannelMessageList> {
  const params = new URLSearchParams({ justification });
  if (cursor) params.set("cursor", cursor);
  return api.get(`/admin/channels/${channelId}/messages?${params.toString()}`);
}
