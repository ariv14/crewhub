import { API_V1 } from "./constants";

class ApiClient {
  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("auth_token");
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    _isRetry = false
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((options.headers as Record<string, string>) || {}),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // Strip trailing slash — FastAPI has redirect_slashes=False so /path/ won't
    // auto-redirect. Routes are defined without trailing slashes.
    const normalizedPath = path.endsWith("/") ? path.slice(0, -1) : path;
    const res = await fetch(`${API_V1}${normalizedPath}`, {
      ...options,
      headers,
    });

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
      // Refresh failed or no user — clear auth state and redirect
      localStorage.removeItem("auth_token");
      document.cookie = "__auth_token=; path=/; max-age=0; SameSite=Strict";
      if (typeof window !== "undefined") {
        window.location.href = "/login";
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

  delete<T>(path: string) {
    return this.request<T>(path, { method: "DELETE" });
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
