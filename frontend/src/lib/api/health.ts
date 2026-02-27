import { API_BASE_URL } from "../constants";

export interface HealthResponse {
  status: string;
  version: string;
  agents_registered: number;
  agents_active: number;
}

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`);
  return res.json();
}
