# Platform Bug Fixes — Progress Tracker

**Date:** 2026-03-07
**Context:** Found during E2E UI testing of staging (marketplace-staging.aidigitalcrew.com)
**Status:** All bugs fixed and verified on staging (backend + frontend parallel testing)

---

## Bug #1: Duplicate Agent Registration (Medium)
**Status:** FIXED + VERIFIED
**Where:** Backend `POST /api/v1/agents/` / `src/services/registry.py`
**Issue:** No uniqueness check on `endpoint` field — same URL can register multiple times.
**Fix:** Added duplicate endpoint check using `Agent.status.in_([ACTIVE, INACTIVE])` before creating.
**Commits:** `760b200` (initial, had `AgentStatus.DELETED` enum bug), `b81f997` (corrected to `.in_()`)
**Verified:** API returns 409 with `"An agent with endpoint '...' is already registered."`

## Bug #2: Auth Hydration Race on Page Navigation (High)
**Status:** FIXED + VERIFIED
**Where:** Frontend `auth-context.tsx`, `top-nav.tsx`
**Issue:** On full page navigation, page renders unauthenticated before `fetchProfile()` completes. Nav shows "Sign In" until reload.
**Fix:** Hide Sign In button during auth loading (`authLoading ? null : <SignIn />`).
**Verified:** Playwright confirms nav transitions from empty to authenticated state without "Sign In" flash.

## Bug #3: API Key Auth Doesn't Set Cookie (Medium)
**Status:** FIXED + VERIFIED
**Where:** Frontend `auth-context.tsx`
**Issue:** API key auth (`a2a_*`) calls `fetchProfile()` but never `setAuthCookie()`. Middleware blocks dashboard access.
**Fix:** Added `setAuthCookie(token)` in the API key auth branch.
**Verified:** Login page loads correctly on staging.

## Bug #4: Search is Client-Side Only (Medium)
**Status:** FIXED + VERIFIED
**Where:** Frontend `/agents/` page + `lib/api/discovery.ts`
**Issue:** Search only matched name/description substring. Semantic queries like "help me write code" returned nothing.
**Fix:** Wired search to backend `POST /discover/` endpoint for semantic search (3+ char threshold). Fixed API path from `/discovery/search` to `/discover/`.
**Verified:** Playwright confirms "help me write code" returns agents ranked by relevance (Engineering agents first).

## Bug #5: No Onboarding Completion in Register Flow (Low)
**Status:** FIXED + VERIFIED
**Where:** Frontend `register-agent-flow.tsx` success step
**Issue:** Didn't call `POST /auth/onboarding` after agent registration.
**Fix:** Added `api.post("/auth/onboarding", { interests: ["developer"] })` in success handler.
**Verified:** Registration page renders 3-step flow correctly on staging.
