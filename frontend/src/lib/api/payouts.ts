// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { api } from "../api-client";

export interface ConnectStatus {
  connected: boolean;
  onboarded: boolean;
  payouts_enabled: boolean;
  account_id: string | null;
}

export interface OnboardingResponse {
  onboarding_url: string;
}

export interface WithdrawableBalance {
  withdrawable_credits: number;
  withdrawable_usd_cents: number;
  pending_clearance_credits: number;
  total_earned_credits: number;
  total_paid_out_credits: number;
  minimum_payout_credits: number;
  credit_to_usd_rate: number;
}

export interface PayoutEstimate {
  gross_usd_cents: number;
  stripe_fee_cents: number;
  net_usd_cents: number;
}

export interface PayoutRecord {
  id: string;
  amount_credits: number;
  amount_usd_cents: number;
  stripe_fee_cents: number;
  status: string;
  stripe_transfer_id: string | null;
  failure_reason: string | null;
  requested_at: string;
  completed_at: string | null;
}

export interface PayoutHistory {
  payouts: PayoutRecord[];
  total: number;
  page: number;
  per_page: number;
}

export async function connectOnboard(): Promise<OnboardingResponse> {
  return api.post("/payouts/connect/onboard", {});
}

export async function getConnectStatus(): Promise<ConnectStatus> {
  return api.get("/payouts/connect/status");
}

export async function getWithdrawableBalance(): Promise<WithdrawableBalance> {
  return api.get("/payouts/balance");
}

export async function getPayoutEstimate(amountCredits: number): Promise<PayoutEstimate> {
  return api.get(`/payouts/estimate?amount_credits=${amountCredits}`);
}

export async function requestPayout(amountCredits: number): Promise<PayoutRecord> {
  return api.post("/payouts/request", { amount_credits: amountCredits });
}

export async function getPayoutHistory(page = 1, perPage = 20): Promise<PayoutHistory> {
  return api.get(`/payouts/history?page=${page}&per_page=${perPage}`);
}
