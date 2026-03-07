/**
 * Build the correct auth headers for a given token.
 * API keys (a2a_*) use X-API-Key; everything else uses Bearer.
 */
export function getAuthHeaders(token: string): Record<string, string> {
  if (token.startsWith("a2a_")) {
    return { "X-API-Key": token };
  }
  return { Authorization: `Bearer ${token}` };
}
