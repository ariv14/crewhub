# httpOnly Cookie Migration Plan

**Date:** 2026-03-19
**Status:** Planned (Week 2)
**Assessed by:** Security Architect + Backend Engineer + QA Tester (3 parallel assessors)

---

## Problem

Auth token stored in `localStorage` — any XSS can steal it for full account takeover (C-FE-1).

## Architecture Constraints

1. Frontend is a **static export** (`output: "export"`) on Cloudflare Pages — no Node.js server
2. `document.cookie` from JS **cannot set httpOnly** — browsers silently ignore the flag
3. Next.js `middleware.ts` is **dead code** in static export — it never runs in production
4. Staging frontend (`marketplace-staging.aidigitalcrew.com`) and API (`api-staging.crewhubai.com`)
   are on **different registrable domains** — cookies can't be shared cross-site
5. Production frontend (`crewhubai.com`) and API (`api.crewhubai.com`) are **same-site** — cookies work
6. API key auth (`a2a_*`) must remain in localStorage — not a short-lived token

## Solution: Dual-Path Auth

Keep `Authorization: Bearer` header for API key users and staging.
Add httpOnly cookie as a parallel auth path for Firebase users on production.

```
Firebase SDK → POST /auth/session (backend) → Set-Cookie: HttpOnly
                                             ↓
Browser auto-sends cookie on all requests → Backend reads Cookie OR Bearer
                                             ↓
API key users → localStorage → X-API-Key header (unchanged)
```

## Implementation Steps

### Step 1: Backend — Session Endpoints (foundation)

Create `POST /auth/session` and `POST /auth/session/logout`:

```python
# src/api/auth.py — new endpoints

@router.post("/session")
async def create_session(
    data: FirebaseTokenRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Exchange Firebase ID token for httpOnly session cookie."""
    decoded = verify_firebase_token(data.id_token)
    # ... same user lookup/creation as /auth/firebase ...

    # Set httpOnly cookie — only works when backend sets it via Set-Cookie header
    cookie_domain = ".crewhubai.com" if not settings.debug else None
    response.set_cookie(
        key="__session",
        value=data.id_token,  # or a backend-issued JWT
        httponly=True,
        secure=True,
        samesite="lax",
        domain=cookie_domain,
        max_age=3600,
        path="/",
    )
    return UserResponse.model_validate(user)


@router.post("/session/logout")
async def logout_session(response: Response):
    """Clear the httpOnly session cookie."""
    response.delete_cookie(
        key="__session",
        httponly=True,
        secure=True,
        samesite="lax",
        domain=".crewhubai.com" if not settings.debug else None,
        path="/",
    )
    return {"message": "Logged out"}
```

### Step 2: Backend — Read Cookie in get_current_user

Add a third auth path after Bearer and API key:

```python
# src/core/auth.py — get_current_user modification

from fastapi import Request, Cookie

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    request: Request = None,  # for cookie reading
) -> dict:
    # 1. Try Bearer token (existing)
    if credentials is not None:
        ...

    # 2. Try API key (existing)
    if x_api_key is not None:
        ...

    # 3. Try httpOnly session cookie (NEW)
    session_cookie = request.cookies.get("__session") if request else None
    if session_cookie:
        if is_firebase_enabled():
            decoded = verify_firebase_token(session_cookie)
            return { "id": decoded["uid"], ... }
        else:
            payload = decode_access_token(session_cookie)
            return { "id": payload["sub"], ... }

    raise UnauthorizedError(detail="Authentication required")
```

### Step 3: Backend — CSRF Protection

Since cookies are auto-sent, add CSRF defense for mutation endpoints:

```python
# src/middleware/csrf.py

async def csrf_protection(request: Request):
    """Reject cookie-authenticated mutations without CSRF token.

    Safe because:
    - Bearer/API-key auth: not affected (no cookie involved)
    - Cookie auth + GET: allowed (read-only, SameSite=Lax blocks cross-site POST)
    - Cookie auth + POST/PUT/PATCH/DELETE: must have matching Origin header
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # If auth came from cookie (no Authorization header), verify Origin
    has_bearer = request.headers.get("authorization")
    has_api_key = request.headers.get("x-api-key")
    has_cookie = request.cookies.get("__session")

    if has_cookie and not has_bearer and not has_api_key:
        origin = request.headers.get("origin", "")
        allowed = {"https://crewhubai.com", "https://www.crewhubai.com",
                    "http://localhost:3000"}  # + staging origins
        if origin not in allowed:
            raise HTTPException(403, "CSRF: origin not allowed")
```

### Step 4: Frontend — Call Session Endpoint

Replace `setAuthCookie()` + localStorage writes with `POST /auth/session`:

```typescript
// auth-context.tsx — modified flow

async function createSession(idToken: string): Promise<void> {
  // Call backend to set httpOnly cookie
  await fetch(`${API_V1}/auth/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
    credentials: "include",  // tells browser to accept Set-Cookie
  });
}

// In Google sign-in:
const idToken = await result.user.getIdToken();
await createSession(idToken);  // sets httpOnly cookie
// Keep localStorage ONLY for API key users, not Firebase
```

### Step 5: Frontend — api-client.ts Changes

```typescript
// api-client.ts — modified request method

private async request<T>(path: string, options: RequestInit = {}, ...): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  // API key users: send as header (from localStorage)
  const apiKey = typeof window !== "undefined"
    ? localStorage.getItem("api_key") : null;  // separate key for a2a_
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  // Firebase users: cookie is sent automatically via credentials: "include"
  const res = await fetch(`${API_V1}${path}`, {
    ...options,
    headers,
    credentials: "include",  // NEW — sends httpOnly cookie automatically
  });
  ...
}
```

### Step 6: Frontend — SSE Hooks

```typescript
// use-activity-feed.ts — use credentials: "include" instead of manual token

const response = await fetch(url, {
  credentials: "include",  // httpOnly cookie sent automatically
  signal: abortController.signal,
});
// Remove: const token = localStorage.getItem("auth_token");
// Remove: manual Authorization header
```

### Step 7: Frontend — Token Refresh

```typescript
// auth-context.tsx — 55-minute refresh interval

setInterval(async () => {
  const user = firebaseAuth?.currentUser;
  if (!user) return;
  try {
    const newToken = await user.getIdToken(true);
    await createSession(newToken);  // refreshes the httpOnly cookie
  } catch {
    // Network blip — don't logout, retry next interval
    console.warn("Token refresh failed, will retry");
  }
}, 55 * 60 * 1000);
```

### Step 8: Frontend — Logout

```typescript
// auth-context.tsx — logout

async function logout() {
  await firebaseSignOut(firebaseAuth);
  // Clear httpOnly cookie via backend (JS can't clear httpOnly cookies)
  await fetch(`${API_V1}/auth/session/logout`, {
    method: "POST",
    credentials: "include",
  }).catch(() => {});
  // Clear API key if present
  localStorage.removeItem("api_key");
  setAuthState({ user: null, loading: false, isAdmin: false });
}
```

## Staging Workaround

Staging has cross-site domains. Two options:

**Option A (recommended): Move staging frontend to `staging.crewhubai.com`**
- Already in the CORS allowlist
- Same-site with `api-staging.crewhubai.com`
- One DNS record change in Cloudflare

**Option B: Keep Bearer header fallback for staging**
- Frontend detects staging via `NEXT_PUBLIC_API_URL` and uses localStorage + Bearer header
- Only production gets httpOnly cookies
- More code paths to maintain

## Pre-Deploy Verification

Before deploying, run these tests:

```bash
# Test 1: CF Worker forwards Set-Cookie
curl -si https://api.crewhubai.com/auth/session \
  -X POST -H "Content-Type: application/json" \
  -d '{"id_token": "<valid-firebase-token>"}' | grep -i set-cookie

# Test 2: HF Spaces Set-Cookie pass-through
curl -si https://arimatch1-crewhub.hf.space/auth/session \
  -X POST -H "Content-Type: application/json" \
  -d '{"id_token": "<valid-firebase-token>"}' | grep -i set-cookie

# Test 3: CSRF protection blocks cross-origin
curl -si https://api.crewhubai.com/api/v1/tasks/ \
  -X POST -H "Content-Type: application/json" \
  -H "Origin: https://evil.com" \
  -H "Cookie: __session=<stolen-token>" | head -5
# Should return 403
```

## Migration Path for Existing Users

1. Deploy backend with `/auth/session` endpoint + cookie reading in `get_current_user`
2. Backend accepts BOTH Bearer header AND cookie — dual auth for the transition period
3. Deploy frontend that calls `/auth/session` on login and sends `credentials: "include"`
4. Existing users: their localStorage token still works (Bearer path) until next login
5. On next login: frontend calls `/auth/session`, backend sets httpOnly cookie
6. After 30 days: remove localStorage token writes from frontend (keep API key in localStorage)

## Files to Modify

| File | Change |
|---|---|
| `src/api/auth.py` | Add `POST /session` and `POST /session/logout` |
| `src/core/auth.py` | Add cookie reading as 3rd auth path in `get_current_user` |
| `src/main.py` | Add CORS `allow_credentials=True` (already set), verify explicit origins |
| `frontend/src/lib/auth-context.tsx` | Replace `setAuthCookie` + localStorage with `createSession()` call |
| `frontend/src/lib/api-client.ts` | Add `credentials: "include"`, separate API key storage |
| `frontend/src/lib/hooks/use-activity-feed.ts` | Use `credentials: "include"` instead of manual token |
| `frontend/src/lib/hooks/use-agent-activity.tsx` | Same as above |
| `frontend/src/app/admin/mcp/page.tsx` | Same as above |
| `frontend/src/components/layout/top-nav.tsx` | Use auth context instead of localStorage check |

## Risk Register

| Risk | Mitigation |
|---|---|
| CF Worker strips Set-Cookie | Test before deploy; if blocked, set cookie at CF Worker level |
| HF Spaces proxy mangles cookie | Test before deploy; domain= attribute may be stripped |
| CSRF on cookie-authenticated mutations | Origin header validation middleware |
| Staging cross-site cookies | Move staging to staging.crewhubai.com |
| API key users broken | Keep separate localStorage key for a2a_ tokens |
| Refresh failure during network blip | Don't logout on failed refresh; retry next interval |
| Existing users force-logged-out | Dual auth (Bearer + Cookie) during 30-day transition |
