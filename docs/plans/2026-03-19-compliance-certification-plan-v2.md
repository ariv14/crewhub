# CrewHub Compliance Certification Plan — v2 (Post Week 1 Fixes)

**Date:** 2026-03-19
**Revision:** v2 — re-assessed after 12 critical/high fixes applied
**Target certifications:** SOC 2 Type II, GDPR, HIPAA-readiness
**Assessment by:** Security Architect + Frontend/Backend/API Auditors (3 parallel assessors)

---

## Executive Summary

Round 1 fixed 12 critical/high findings (XSS, SSRF, auth on workflow runs, security headers,
cookie hardening, webhook enforcement, import bugs). This v2 re-assessment verifies those fixes
and identifies **34 remaining gaps** — down from the original 64.

**Biggest remaining risks:**
1. Auth token in localStorage (XSS → full account takeover still possible)
2. Audit log model exists but is not wired into any admin endpoint (SOC 2 blocker)
3. PostHog tracks PII without consent (GDPR Article 6 violation)
4. Privacy policy makes 2 false claims about tracking behavior
5. Several endpoints still lack rate limiting or auth

---

## Verified Fixes (12 items — confirmed in code)

| # | Fix | Evidence |
|---|---|---|
| 1 | `AsyncSessionLocal` import bug | `main.py` uses `async_session` throughout |
| 2 | `abuse_detector.py` import path | Imports from `src.core.rate_limiter` |
| 3 | Webhooks reject when secret unset (prod) | `webhooks.py:29-35` — debug-only skip, prod raises 503 |
| 4 | Workflow run endpoints require auth | `workflows.py` — `resolve_db_user_id` + ownership check |
| 5 | SSRF protection on detect/validate | `url_validator.py` blocks private IPs, both endpoints use it |
| 6 | Activity stream scoped to user | `activity.py:66,132` — Task + Transaction filtered by user_id |
| 7 | Security headers (CSP, HSTS, X-Frame-Options) | `public/_headers` file, verified via curl |
| 8 | XSS prevention — rehype-sanitize | Both ReactMarkdown instances sanitized |
| 9 | E2E bypass gated behind env var | `auth-context.tsx:94-97` — requires `NEXT_PUBLIC_E2E_TEST` |
| 10 | Secure flag on cookies | `auth-context.tsx:52`, `api-client.ts:65` |
| 11 | Image URL validation (HTTPS only) | `task-artifacts-display.tsx:88-99` |
| 12 | Workflow clone visibility check | `workflow_service.py:240-243` — private check on clone |

---

## Remaining Gaps (34 items)

### CRITICAL (2)

| ID | Area | Finding | File | Fix |
|----|------|---------|------|-----|
| C-1 | Auth | Auth token still in localStorage — XSS → account takeover | `auth-context.tsx:66,120,144,173,188,200` | Migrate to server-set httpOnly cookie via auth exchange endpoint |
| C-2 | Audit | `audit_log()` exists but is NOT wired into any admin endpoint — SOC 2 blocker | `admin.py` (entire file, 0 calls to audit_log) | Wire into all 11 mutation endpoints |

### HIGH (14)

| ID | Area | Finding | File | Fix |
|----|------|---------|------|-----|
| H-1 | GDPR | PostHog loads without consent — no banner, no opt-in | `posthog-provider.tsx:43` | Add consent banner, gate PostHog init |
| H-2 | GDPR | `maskAllInputs: false` — session recordings capture form content | `posthog-provider.tsx:92` | Set `maskAllInputs: true` |
| H-3 | GDPR | `posthog.identify()` sends email+name without consent | `posthog-provider.tsx:103-106` | Gate behind consent, or remove identify() |
| H-4 | GDPR | Privacy policy falsely claims "no PII in PostHog" | `privacy/page.tsx:53` | Fix text to match actual behavior |
| H-5 | GDPR | Privacy policy falsely claims DNT is respected | `privacy/page.tsx:53` | Implement DNT check or remove claim |
| H-6 | Sentry | No PII scrubbing — send_default_pii not set, no EventScrubber | `main.py:111-116` | Add scrubber denylist |
| H-7 | Auth | Bootstrap admin: no rate limit, no secret, TOCTOU race | `admin.py:36-62` | Add rate limit, BOOTSTRAP_SECRET, SELECT FOR UPDATE |
| H-8 | Rate | `rate_limit_by_ip` uses proxy IP, not real client IP | `rate_limiter.py:179` | Use CF-Connecting-IP / X-Forwarded-For |
| H-9 | Access | `GET /workflows/{id}` has no auth — private workflows readable | `workflows.py:64-70` | Add auth + is_public/owner check |
| H-10 | Access | `GET /crews/{id}` has no auth — private crews readable | `crews.py:64-71` | Add auth + visibility check |
| H-11 | Auth | `POST /builder/verify-code` — no auth, no rate limit, in-memory store | `builder.py:78-91` | Add rate_limit_by_ip, move codes to Redis |
| H-12 | Rate | Supervisor plan/replan/approve — no rate limit on LLM endpoints | `supervisor.py:28,41,54` | Add rate_limit_dependency |
| H-13 | Rate | `POST /feedback` — no rate limit, Discord spam amplifier | `feedback.py:23` | Add rate_limit_by_ip |
| H-14 | Rate | `POST /telemetry/events` — no rate limit, no batch size cap | `telemetry.py:26` | Add rate_limit_by_ip + max_length=100 on events list |

### MEDIUM (12)

| ID | Area | Finding | File |
|----|------|---------|------|
| M-1 | GDPR | No "Delete Account" or "Download Data" UI in Settings | `settings/page.tsx` |
| M-2 | GDPR | No privacy policy link on registration form | `register/page.tsx` |
| M-3 | GDPR | No data export endpoint (backend) | Missing endpoint |
| M-4 | GDPR | No account deletion endpoint (backend) | Missing endpoint |
| M-5 | GDPR | No consent tracking on User model | Missing columns |
| M-6 | Rate | Admin endpoints have zero rate limiting | `admin.py` (all endpoints) |
| M-7 | Access | `GET /analytics/delegation-accuracy` public — leaks business metrics | `analytics.py:110-114` |
| M-8 | Config | `SENTRY_DSN` not in Settings model — unvalidated | `config.py` (absent) |
| M-9 | Data | `GET /admin/llm-calls/{id}` exposes unscrubbed request/response bodies | `llm_calls.py:85-98` |
| M-10 | Auth | Middleware checks cookie existence only, not validity | `middleware.ts:26-33` |
| M-11 | Telemetry | Telemetry events batch has no max_items constraint | `telemetry.py` schema |
| M-12 | Validate | `/validate` 30s timeout — resource exhaustion via slow connections | `validate.py:284` |

### LOW (6)

| ID | Finding |
|----|---------|
| L-1 | `global-error.tsx` missing — root layout crashes unhandled |
| L-2 | Login/register forms missing `autoComplete` attributes |
| L-3 | CSP has `unsafe-inline` + `unsafe-eval` (Next.js constraint) |
| L-4 | Debug health endpoints return 200 in prod (should be 404/403) |
| L-5 | Agent registration events in activity stream are platform-wide |
| L-6 | Workflow clone leaks UUID existence (404 vs 403 on private) |

---

## Updated Implementation Plan

### Phase 1: Wire Audit Logging + Quick Fixes (1-2 days)

**Backend:**
1. [ ] Wire `audit_log()` into all 11 admin mutation endpoints (C-2)
2. [ ] Sentry PII scrubbing — add `send_default_pii=False` + `EventScrubber` denylist (H-6)
3. [ ] Fix `rate_limit_by_ip` to use `CF-Connecting-IP` / `X-Forwarded-For` (H-8)
4. [ ] Add `rate_limit_by_ip` to: feedback, telemetry, builder/verify-code (H-13, H-14, H-11)
5. [ ] Add `rate_limit_dependency` to: supervisor plan/replan/approve (H-12)
6. [ ] Add `max_length=100` to telemetry events batch schema (M-11)
7. [ ] Bootstrap admin: add `rate_limit_by_ip`, `BOOTSTRAP_SECRET` env var, `SELECT FOR UPDATE` (H-7)
8. [ ] Add auth + visibility to `GET /workflows/{id}` and `GET /crews/{id}` (H-9, H-10)

**Frontend:**
9. [ ] Fix privacy policy: remove false claims about PostHog PII and DNT (H-4, H-5)
10. [ ] Set `maskAllInputs: true` in PostHog session recording config (H-2)
11. [ ] Create `global-error.tsx` (L-1)
12. [ ] Add `autoComplete` attributes to login/register forms (L-2)

### Phase 2: Auth Architecture + GDPR Quick Wins (1 week)

**Auth migration (C-1 — last remaining CRITICAL):**
1. [ ] Backend: `POST /auth/session` — receives Firebase token, sets httpOnly cookie
2. [ ] Backend: CORS changes — `credentials: "include"`, explicit origin (not `*`)
3. [ ] Frontend: rewrite api-client.ts to use cookie-based auth (drop Authorization header)
4. [ ] Frontend: rewrite auth-context.tsx token refresh to go through session endpoint
5. [ ] Handle cross-origin cookies (crewhubai.com ↔ api.crewhubai.com)
6. [ ] Migration plan for existing logged-in users

**GDPR quick wins (in parallel):**
7. [ ] Cookie consent banner — gate PostHog init + identify (H-1, H-3)
8. [ ] Check `navigator.doNotTrack` and call `posthog.opt_out_capturing()` (H-5)
9. [ ] Fix privacy policy: remove false claims about PostHog PII and DNT (H-4, H-5)
10. [ ] Privacy policy + terms links on registration form (M-2)

### Phase 3: GDPR Endpoints + SOC 2 Controls (1 week)

**GDPR:**
1. [ ] `GET /api/v1/auth/me/export` — user data export (M-3)
2. [ ] `DELETE /api/v1/auth/me` — account deletion with 30-day PII purge (M-4)
3. [ ] Add `consent_version`, `consent_given_at` columns to User model (M-5)
4. [ ] "Delete Account" + "Download My Data" buttons in Settings (M-1)

**SOC 2:**
5. [ ] RBAC admin roles (super/ops/billing)
6. [ ] Separate ENCRYPTION_KEY from SECRET_KEY + key rotation path
7. [ ] Add auth + visibility to `GET /workflows/{id}` and `GET /crews/{id}` (H-9, H-10)

### Phase 4: Hardening + Audit Prep (1 week)

1. [ ] Enforce Redis for rate limiting in production
2. [ ] `pip-audit` in CI pipeline
3. [ ] Move debug health endpoints to conditional router registration
4. [ ] Add auth to `/analytics/delegation-accuracy`
5. [ ] Reduce validate.py timeout from 30s to 10s
6. [ ] Move builder exchange codes to Redis
7. [ ] Document incident response / breach notification procedure
8. [ ] Create DPA template for enterprise
9. [ ] Write SOC 2 controls mapping (CC1-CC9)
10. [ ] Engage SOC 2 auditor for readiness assessment

---

## Severity Summary

| Severity | Original (v1) | After fixes | Still open |
|----------|---------------|-------------|------------|
| CRITICAL | 12 | -10 fixed | **2** |
| HIGH | 22 | -8 fixed | **14** |
| MEDIUM | 18 | -0 fixed | **12** (some new) |
| LOW | 12 | -6 resolved | **6** |
| **Total** | **64** | **-24 fixed** | **34** |

---

## Top 3 Attack Chains Still Open

1. **XSS → Token Theft**: CSP has `unsafe-inline`, token in localStorage, PostHog session
   recordings capture form inputs → malicious inline script steals token from localStorage

2. **Admin Bootstrap Race**: Fresh deploy → two concurrent requests → both pass admin_count=0
   check → two admin accounts created → attacker has permanent admin

3. **Discord/DB Spam**: `POST /feedback` (no auth, no rate limit) and `POST /telemetry/events`
   (no auth, no rate limit, no batch cap) → flood Discord webhook + fill database
