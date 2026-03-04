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
    document.cookie = `__auth_token=${token}; path=/; max-age=3600; SameSite=Strict`;
  } else {
    document.cookie = "__auth_token=; path=/; max-age=0; SameSite=Strict";
  }
}

/**
 * Force-refresh the current user's Firebase ID token and update storage.
 * Returns the new token, or null if no user is signed in.
 */
export async function refreshToken(): Promise<string | null> {
  const user = fbAuth?.currentUser;
  if (!user) return null;
  const token = await user.getIdToken(true);
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
      typeof window !== "undefined" &&
      localStorage.getItem("__playwright_auth__") === "1";
    const storedToken =
      typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    const isApiKeyAuth = storedToken?.startsWith("a2a_");

    if (!isFirebaseMode || !firebaseAuth || isTestBypass || isApiKeyAuth) {
      // Local JWT mode: check for stored token
      const token = localStorage.getItem("auth_token");
      if (token) {
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
          localStorage.setItem("auth_token", idToken);
          setAuthCookie(idToken);
          // Exchange Firebase token with our backend
          try {
            await api.post("/auth/firebase", { id_token: idToken });
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
          localStorage.setItem("auth_token", newToken);
          setAuthCookie(newToken);
        } catch {
          // Token refresh failed — user will re-auth on next API call
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
    // Set token + cookie NOW so middleware sees auth on the next navigation.
    // Without this, router.push("/dashboard") races ahead of onAuthStateChanged
    // and middleware redirects back to /login (no cookie yet).
    const idToken = await result.user.getIdToken();
    localStorage.setItem("auth_token", idToken);
    setAuthCookie(idToken);
    await api.post("/auth/firebase", { id_token: idToken });
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
    localStorage.removeItem("auth_token");
    setAuthCookie(null);
    setState({ user: null, loading: false, isAdmin: false });
  }, [isFirebaseMode]);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        loginWithGoogle,
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
