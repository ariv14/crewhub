// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { API_V1 } from "./constants";

/**
 * Whether the API is on the same site as the frontend (shared parent domain).
 * When true, httpOnly cookies can be used. When false (staging cross-site),
 * we skip credentials: "include" to avoid CORS conflicts with wildcard origin.
 */
function isSameSite(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const apiHost = new URL(API_V1).hostname;
    const pageHost = window.location.hostname;
    // Same parent domain: crewhubai.com ↔ api.crewhubai.com
    const apiRoot = apiHost.split(".").slice(-2).join(".");
    const pageRoot = pageHost.split(".").slice(-2).join(".");
    return apiRoot === pageRoot;
  } catch {
    return false;
  }
}

class ApiClient {
  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("auth_token");
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    _isRetry = false,
    _retryCount = 0
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((options.headers as Record<string, string>) || {}),
    };

    if (token) {
      if (token.startsWith("a2a_")) {
        headers["X-API-Key"] = token;
      } else {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }

    let res: Response;
    try {
      res = await fetch(`${API_V1}${path}`, {
        ...options,
        headers,
        ...(isSameSite() ? { credentials: "include" as RequestCredentials } : {}),
      });
    } catch (err) {
      // Network error (offline, DNS failure, etc.) — retry
      if (_retryCount < 2) {
        await new Promise((r) => setTimeout(r, 1000 * 2 ** _retryCount));
        return this.request<T>(path, options, _isRetry, _retryCount + 1);
      }
      throw new ApiError(0, "Network error — please check your connection");
    }

    // Retry on 5xx server errors (HF Spaces cold starts)
    if (res.status >= 500 && _retryCount < 2) {
      await new Promise((r) => setTimeout(r, 1000 * 2 ** _retryCount));
      return this.request<T>(path, options, _isRetry, _retryCount + 1);
    }

    // On 401, attempt a single token refresh before failing
    if (res.status === 401 && !_isRetry) {
      try {
        const { refreshToken } = await import("./auth-context");
        const newToken = await refreshToken();
        if (newToken) {
          return this.request<T>(path, options, true);
        }
      } catch {
        // refresh failed — fall through to clear auth
      }
      // Refresh failed or no user — clear auth state
      localStorage.removeItem("auth_token");
      document.cookie = "__auth_token=; path=/; max-age=0; SameSite=Strict; Secure";
      // Only redirect to /login from protected pages (dashboard, admin).
      // Public pages (/, /agents, /register-agent, /login, /register) should
      // NOT be hijacked — they work fine without auth.
      if (typeof window !== "undefined") {
        const p = window.location.pathname;
        const isProtected =
          p.startsWith("/dashboard") || p.startsWith("/admin");
        if (isProtected) {
          window.location.href = "/login";
        }
      }
      throw new ApiError(401, "Session expired");
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, body.detail || "Request failed");
    }

    if (res.status === 204) return undefined as T;
    return res.json();
  }

  get<T>(path: string) {
    return this.request<T>(path);
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  put<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  patch<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  delete<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: "DELETE",
      body: body ? JSON.stringify(body) : undefined,
    });
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

export const api = new ApiClient();
