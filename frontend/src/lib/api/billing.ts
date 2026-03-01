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

export async function getSubscriptionStatus(): Promise<SubscriptionStatus> {
  return api.get("/billing/status");
}

export async function createCheckoutSession(): Promise<CheckoutResponse> {
  return api.post("/billing/checkout", {});
}

export async function createPortalSession(): Promise<PortalResponse> {
  return api.post("/billing/portal", {});
}
