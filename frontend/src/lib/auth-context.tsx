// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  GithubAuthProvider,
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  signOut as firebaseSignOut,
  type User as FirebaseUser,
} from "firebase/auth";
import { auth as firebaseAuth, isFirebaseConfigured } from "./firebase";
import { api } from "./api-client";
import type { User } from "@/types/auth";
import { auth as fbAuth } from "./firebase";

interface AuthState {
  user: User | null;
  loading: boolean;
  isAdmin: boolean;
}

interface AuthContextType extends AuthState {
  loginWithGoogle: () => Promise<void>;
  loginWithGitHub: () => Promise<void>;
  loginWithEmail: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  isFirebaseMode: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

/**
 * Sync the auth token to a cookie so Next.js middleware can read it
 * for server-side route protection. The cookie is httpOnly=false
 * (needs to be readable by middleware) but SameSite=Strict.
 */
function setAuthCookie(token: string | null) {
  if (token) {
    document.cookie = `__auth_token=${token}; path=/; max-age=3600; SameSite=Strict; Secure`;
  } else {
    document.cookie = "__auth_token=; path=/; max-age=0; SameSite=Strict; Secure";
  }
}

/**
 * Create/refresh the httpOnly session cookie by exchanging a Firebase token
 * with the backend. Only works on same-site deployments (production).
 * On cross-site staging, this is a no-op and Bearer header is used instead.
 */
async function createSession(idToken: string): Promise<void> {
  const { API_V1 } = await import("./constants");
  // Only set httpOnly cookie on same-site deployments (production)
  try {
    const apiHost = new URL(API_V1).hostname;
    const pageHost = typeof window !== "undefined" ? window.location.hostname : "";
    const apiRoot = apiHost.split(".").slice(-2).join(".");
    const pageRoot = pageHost.split(".").slice(-2).join(".");
    if (apiRoot !== pageRoot) return; // cross-site — skip cookie, use Bearer
  } catch {
    return;
  }
  try {
    await fetch(`${API_V1}/auth/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_token: idToken }),
      credentials: "include",
    });
  } catch {
    // CORS may block credentials:include if proxy returns wildcard origin.
    // Silently skip — Bearer header from localStorage is the fallback.
  }
}

/**
 * Force-refresh the current user's Firebase ID token and update session.
 * Returns the new token, or null if no user is signed in.
 */
export async function refreshToken(): Promise<string | null> {
  const user = fbAuth?.currentUser;
  if (!user) return null;
  const token = await user.getIdToken(true);
  // Update httpOnly session cookie via backend
  try {
    await createSession(token);
  } catch {
    // Network blip — keep old cookie, don't logout
  }
  // Also update localStorage as fallback (for SSE hooks during transition)
  localStorage.setItem("auth_token", token);
  setAuthCookie(token);
  return token;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    isAdmin: false,
  });

  const isFirebaseMode = isFirebaseConfigured();

  const fetchProfile = useCallback(async () => {
    try {
      const user = await api.get<User>("/auth/me");
      setState({ user, loading: false, isAdmin: user.is_admin ?? false });
    } catch {
      setState({ user: null, loading: false, isAdmin: false });
    }
  }, []);

  // Firebase auth state listener
  useEffect(() => {
    // Skip Firebase listener when using API key auth or E2E test bypass.
    // API keys (a2a_...) are managed outside Firebase and should not be
    // cleared by onAuthStateChanged.
    const isTestBypass =
      process.env.NEXT_PUBLIC_E2E_TEST === "true" &&
      typeof window !== "undefined" &&
      localStorage.getItem("__playwright_auth__") === "1";
    const storedToken =
      typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    const isApiKeyAuth = storedToken?.startsWith("a2a_");

    if (!isFirebaseMode || !firebaseAuth || isTestBypass || isApiKeyAuth) {
      // Local JWT / API key mode: check for stored token
      const token = localStorage.getItem("auth_token");
      if (token) {
        // Sync token to cookie so Next.js middleware allows protected routes
        setAuthCookie(token);
        fetchProfile();
      } else {
        setState((s) => ({ ...s, loading: false }));
      }
      return;
    }

    const unsubscribe = onAuthStateChanged(
      firebaseAuth,
      async (firebaseUser: FirebaseUser | null) => {
        if (firebaseUser) {
          const idToken = await firebaseUser.getIdToken();
          // Set httpOnly session cookie via backend
          try {
            await createSession(idToken);
          } catch {
            // Fallback: keep using Bearer header path
          }
          // Keep localStorage + non-httpOnly cookie as fallback during transition
          localStorage.setItem("auth_token", idToken);
          setAuthCookie(idToken);
          try {
            await fetchProfile();
          } catch {
            setState({ user: null, loading: false, isAdmin: false });
          }
        } else {
          localStorage.removeItem("auth_token");
          setAuthCookie(null);
          setState({ user: null, loading: false, isAdmin: false });
        }
      }
    );

    // Auto-refresh Firebase token 5 min before expiry (tokens last 60 min)
    const REFRESH_INTERVAL_MS = 55 * 60 * 1000; // 55 minutes
    const refreshInterval = setInterval(async () => {
      const currentUser = firebaseAuth?.currentUser;
      if (currentUser) {
        try {
          const newToken = await currentUser.getIdToken(true);
          // Refresh httpOnly session cookie
          await createSession(newToken).catch(() => {});
          // Keep localStorage fallback during transition
          localStorage.setItem("auth_token", newToken);
          setAuthCookie(newToken);
        } catch {
          // Token refresh failed — don't logout, retry next interval
        }
      }
    }, REFRESH_INTERVAL_MS);

    return () => {
      unsubscribe();
      clearInterval(refreshInterval);
    };
  }, [isFirebaseMode, fetchProfile]);

  const isTauri = typeof window !== "undefined" && !!(window as unknown as Record<string, unknown>).__TAURI__;

  const loginWithGoogle = useCallback(async () => {
    if (!firebaseAuth) throw new Error("Firebase not configured");
    const provider = new GoogleAuthProvider();
    // Tauri webview blocks popups — use redirect flow instead
    if (isTauri) {
      await signInWithRedirect(firebaseAuth, provider);
      return; // redirect flow — onAuthStateChanged handles it on return
    }
    const result = await signInWithPopup(firebaseAuth, provider);
    const idToken = await result.user.getIdToken();
    // Set httpOnly session cookie via backend (primary auth)
    await createSession(idToken).catch(() => {});
    // Keep localStorage + cookie as fallback during transition
    localStorage.setItem("auth_token", idToken);
    setAuthCookie(idToken);
    await fetchProfile();
  }, [isTauri, fetchProfile]);

  const loginWithGitHub = useCallback(async () => {
    if (!firebaseAuth) throw new Error("Firebase not configured");
    const provider = new GithubAuthProvider();
    if (isTauri) {
      await signInWithRedirect(firebaseAuth, provider);
      return;
    }
    const result = await signInWithPopup(firebaseAuth, provider);
    const idToken = await result.user.getIdToken();
    await createSession(idToken).catch(() => {});
    localStorage.setItem("auth_token", idToken);
    setAuthCookie(idToken);
    await fetchProfile();
  }, [isTauri, fetchProfile]);

  const loginWithEmail = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await api.post<{ access_token: string }>(
        "/auth/login",
        { email, password, name: "" }
      );
      localStorage.setItem("auth_token", access_token);
      setAuthCookie(access_token);
      await fetchProfile();
    },
    [fetchProfile]
  );

  const register = useCallback(
    async (email: string, password: string, name: string) => {
      await api.post("/auth/register", { email, password, name });
      await loginWithEmail(email, password);
    },
    [loginWithEmail]
  );

  const logout = useCallback(async () => {
    if (isFirebaseMode && firebaseAuth) {
      await firebaseSignOut(firebaseAuth);
    }
    // Clear httpOnly session cookie via backend (JS can't clear httpOnly cookies)
    try {
      const { API_V1 } = await import("./constants");
      const apiHost = new URL(API_V1).hostname;
      const pageHost = window.location.hostname;
      const apiRoot = apiHost.split(".").slice(-2).join(".");
      const pageRoot = pageHost.split(".").slice(-2).join(".");
      if (apiRoot === pageRoot) {
        await fetch(`${API_V1}/auth/session/logout`, {
          method: "POST",
          credentials: "include",
        });
      }
    } catch {
      // Logout continues even if session clear fails
    }
    // Clear localStorage fallback
    localStorage.removeItem("auth_token");
    setAuthCookie(null);
    setState({ user: null, loading: false, isAdmin: false });
  }, [isFirebaseMode]);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        loginWithGoogle,
        loginWithGitHub,
        loginWithEmail,
        register,
        logout,
        refreshUser: fetchProfile,
        isFirebaseMode,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
