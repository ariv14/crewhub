// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as payoutsApi from "../api/payouts";
import { useAuth } from "../auth-context";

export function useConnectStatus() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["payouts", "connect-status"],
    queryFn: payoutsApi.getConnectStatus,
    enabled: !!user,
  });
}

export function useWithdrawableBalance() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["payouts", "balance"],
    queryFn: payoutsApi.getWithdrawableBalance,
    enabled: !!user,
  });
}

export function usePayoutEstimate(amountCredits: number) {
  return useQuery({
    queryKey: ["payouts", "estimate", amountCredits],
    queryFn: () => payoutsApi.getPayoutEstimate(amountCredits),
    enabled: amountCredits >= 2500,
  });
}

export function usePayoutHistory(page = 1, perPage = 20) {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["payouts", "history", page, perPage],
    queryFn: () => payoutsApi.getPayoutHistory(page, perPage),
    enabled: !!user,
  });
}

export function useRequestPayout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (amountCredits: number) => payoutsApi.requestPayout(amountCredits),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["payouts"] });
      qc.invalidateQueries({ queryKey: ["credits", "balance"] });
    },
  });
}

export function useConnectOnboard() {
  return useMutation({
    mutationFn: () => payoutsApi.connectOnboard(),
  });
}
