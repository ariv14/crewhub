import { api } from "../api-client";

export interface BillingStatus {
  account_tier: string;
  stripe_customer_id: string | null;
}

export interface CheckoutResponse {
  checkout_url: string;
}

export interface CreditPack {
  credits: number;
  price_cents: number;
  label: string;
  savings: string | null;
}

export interface CreditPacksResponse {
  packs: CreditPack[];
}

export async function getBillingStatus(): Promise<BillingStatus> {
  return api.get("/billing/status");
}

export async function createCreditsCheckout(amount: number): Promise<CheckoutResponse> {
  return api.post("/billing/credits-checkout", { amount });
}

export async function getCreditPacks(): Promise<CreditPacksResponse> {
  return api.get("/billing/credit-packs");
}
