import { api } from "../api-client";

export interface SubscriptionStatus {
  account_tier: "free" | "premium";
  has_subscription: boolean;
  stripe_customer_id: string | null;
}

export interface CheckoutResponse {
  checkout_url: string;
}

export interface PortalResponse {
  portal_url: string;
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

export async function getSubscriptionStatus(): Promise<SubscriptionStatus> {
  return api.get("/billing/status");
}

export async function createCheckoutSession(): Promise<CheckoutResponse> {
  return api.post("/billing/checkout", {});
}

export async function createCreditsCheckout(amount: number): Promise<CheckoutResponse> {
  return api.post("/billing/credits-checkout", { amount });
}

export async function getCreditPacks(): Promise<CreditPacksResponse> {
  return api.get("/billing/credit-packs");
}

export async function createPortalSession(): Promise<PortalResponse> {
  return api.post("/billing/portal", {});
}
