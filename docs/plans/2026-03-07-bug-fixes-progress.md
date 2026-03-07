# Platform Bug Fixes — Progress Tracker

**Date:** 2026-03-07
**Context:** Found during E2E UI testing of staging (marketplace-staging.aidigitalcrew.com)

---

## Bug #1: Duplicate Agent Registration (Medium)
**Status:** ✅ Fixed
**Where:** Backend `POST /api/v1/agents/`
**Issue:** No uniqueness check on `endpoint` field — same URL can register multiple times.
**Fix:** Add duplicate endpoint check in `TaskBrokerService` or agents API before creating.

## Bug #2: Auth Hydration Race on Page Navigation (High)
**Status:** ✅ Fixed
**Where:** Frontend `auth-context.tsx`
**Issue:** On full page navigation, page renders unauthenticated before `fetchProfile()` completes. Dashboard shows blank, nav shows "Sign In" until reload.
**Fix:** Show loading spinner during auth hydration instead of unauthenticated UI.

## Bug #3: API Key Auth Doesn't Set Cookie (Medium)
**Status:** ✅ Fixed
**Where:** Frontend `auth-context.tsx:97-106`
**Issue:** API key auth (`a2a_*`) calls `fetchProfile()` but never `setAuthCookie()`. Middleware blocks dashboard access.
**Fix:** Add `setAuthCookie(token)` in the API key auth branch.

## Bug #4: Search is Client-Side Only (Medium)
**Status:** ✅ Fixed
**Where:** Frontend `/agents/` page
**Issue:** Search only matches name/description substring. Semantic queries like "help me write code" return nothing.
**Fix:** Wire search to backend `POST /discover/` endpoint for semantic search.

## Bug #5: No Onboarding Completion in Register Flow (Low)
**Status:** ✅ Fixed
**Where:** Frontend `register-agent-flow.tsx` success step
**Issue:** Doesn't call `POST /auth/onboarding` after registration.
**Fix:** Call onboarding completion in success handler.
