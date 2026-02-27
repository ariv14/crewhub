import { api } from "../api-client";
import type { PricingModel } from "@/types/agent";

export interface OpenClawImportRequest {
  skill_url: string;
  pricing: PricingModel;
  category: string;
  tags: string[];
}

export interface OpenClawImportResponse {
  agent_id: string;
  name: string;
  status: string;
  source: string;
  source_url: string;
  message: string;
}

export async function importOpenClaw(
  data: OpenClawImportRequest
): Promise<OpenClawImportResponse> {
  return api.post("/imports/openclaw", data);
}
