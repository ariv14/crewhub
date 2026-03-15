// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as creditsApi from "../api/credits";
import { useAuth } from "../auth-context";

export function useBalance() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["credits", "balance"],
    queryFn: creditsApi.getBalance,
    enabled: !!user,
  });
}

export function useTransactions(
  params?: Parameters<typeof creditsApi.listTransactions>[0]
) {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["credits", "transactions", params],
    queryFn: () => creditsApi.listTransactions(params),
    enabled: !!user,
  });
}

export function useUsage(period?: string) {
  return useQuery({
    queryKey: ["credits", "usage", period],
    queryFn: () => creditsApi.getUsage(period),
  });
}

export function useSpendByAgent(period?: string) {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["credits", "spend-by-agent", period],
    queryFn: () => creditsApi.getSpendByAgent(period),
    enabled: !!user,
  });
}

export function usePurchaseCredits() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (amount: number) => creditsApi.purchaseCredits(amount),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["credits"] });
    },
  });
}
