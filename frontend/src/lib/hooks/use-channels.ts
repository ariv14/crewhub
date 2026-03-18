// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../auth-context";
import * as channelsApi from "../api/channels";
import type { ChannelCreate, ChannelUpdate } from "@/types/channel";

export function useChannels() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["channels"],
    queryFn: channelsApi.getChannels,
    enabled: !!user,
    refetchInterval: 30000,
  });
}

export function useChannel(id: string) {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["channels", id],
    queryFn: () => channelsApi.getChannel(id),
    enabled: !!user && !!id,
  });
}

export function useCreateChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ChannelCreate) => channelsApi.createChannel(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["channels"] });
    },
  });
}

export function useUpdateChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ChannelUpdate }) =>
      channelsApi.updateChannel(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["channels"] });
    },
  });
}

export function useDeleteChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => channelsApi.deleteChannel(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["channels"] });
    },
  });
}

export function useChannelAnalytics(id: string, days = 7) {
  return useQuery({
    queryKey: ["channel-analytics", id, days],
    queryFn: () => channelsApi.getChannelAnalytics(id, days),
    enabled: !!id,
    staleTime: 60000,
  });
}

export function useTestChannel() {
  return useMutation({
    mutationFn: (id: string) => channelsApi.testChannel(id),
  });
}
