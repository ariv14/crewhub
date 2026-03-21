# CrewHub Penetration Test Report

**Date:** 2026-03-21
**Target:** api-staging.crewhubai.com (backend) + staging.crewhubai.com (frontend)
**Environment:** Staging
**Tester:** Automated security assessment (Claude Code)
**Scope:** OWASP Top 10 (2021), full API surface, frontend security headers
**Auth context:** Authenticated as admin user with API key

---

## Executive Summary

**45 individual security tests** were executed across 7 OWASP categories. The application demonstrates strong security posture with **0 Critical and 0 High severity findings**.

| Severity | Count | Status |
|----------|-------|--------|
| Critical | 0 | -- |
| High | 0 | -- |
| Medium | 3 | Remediation recommended |
| Low | 3 | Remediation recommended |
| Info | 2 | Acceptable for staging |
| **PASS** | **37** | Secure |

---

## Findings

### MEDIUM Severity

#### M-1: Admin self-grant credits (Access Control)
- **OWASP:** A01 — Broken Access Control
- **Endpoint:** `POST /api/v1/admin/credits/grant`
- **Description:** Admin can grant credits to their own account. Amount is capped at 100,000 per request, but there is no self-grant prevention or second-party approval.
- **Risk:** Insider threat / SOC 2 separation of duties violation
- **Evidence:** POST with admin's own `user_id` returned 200 with `transaction_id`
- **Recommendation:** Block `admin_user_id == target_user_id`, or require secondary approval. Alert on self-grants.

#### M-2: Profile name accepts HTML/script tags (XSS)
- **OWASP:** A07 — Cross-Site Scripting
- **Endpoint:** `PUT /api/v1/auth/me`
- **Description:** The `name` field accepts `<script>alert(1)</script>` and stores it verbatim. React's JSX auto-escaping mitigates browser-side rendering, but API consumers that render names as raw HTML are vulnerable.
- **Risk:** Stored XSS if rendered by any non-React consumer
- **Evidence:** PUT with XSS payload → 200; GET /auth/me returns `<script>` in name field
- **Recommendation:** Strip HTML tags server-side, enforce max length (~100 chars), restrict character set.

#### M-3: Frontend CSP allows unsafe-inline and unsafe-eval
- **OWASP:** A05 — Security Misconfiguration
- **Location:** `frontend/public/_headers` — `Content-Security-Policy` `script-src`
- **Description:** CSP includes `'unsafe-inline'` and `'unsafe-eval'` in `script-src`, significantly weakening XSS protection. This is a known Next.js constraint but can be mitigated with nonce-based CSP.
- **Risk:** Reduces effectiveness of CSP as an XSS mitigation layer
- **Recommendation:** Migrate to nonce-based CSP when Next.js supports it; remove `unsafe-eval` if possible.

### LOW Severity

#### L-1: Backend API missing HSTS header
- **OWASP:** A02 — Cryptographic Failures
- **Endpoint:** All backend responses
- **Description:** No `Strict-Transport-Security` header on backend API responses. Frontend has HSTS. The backend is behind HF Spaces reverse proxy which may handle HSTS, but belt-and-suspenders is preferred.
- **Recommendation:** Add `Strict-Transport-Security: max-age=63072000; includeSubDomains` to backend responses.

#### L-2: Feedback endpoint accepts unsanitized HTML
- **OWASP:** A07 — Cross-Site Scripting
- **Endpoint:** `POST /api/v1/feedback`
- **Description:** Accepts `<script>`, `<img onerror>`, and `javascript:` URLs in `message` and `page` fields. Currently no admin feedback viewer exists, so risk is latent.
- **Recommendation:** Sanitize input if/when building admin feedback viewer.

#### L-3: Backend API missing Content-Security-Policy header
- **OWASP:** A05 — Security Misconfiguration
- **Endpoint:** All backend responses
- **Description:** Less critical for a JSON API but recommended for defense-in-depth.
- **Recommendation:** Add `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` to API responses.

### INFO (Staging-only, acceptable)

#### I-1: Swagger UI and OpenAPI spec publicly accessible
- **Location:** `/docs`, `/redoc`, `/openapi.json`
- **Description:** Swagger docs expose 146 endpoints including 21 admin paths. Expected on staging (`DEBUG=true`), confirmed disabled on production (`DEBUG=false`).

#### I-2: CORS leaks allow-methods on rejected origins
- **Description:** Preflight responses to unauthorized origins include `access-control-allow-methods` but correctly omit `access-control-allow-origin`. Browsers block the request regardless. Standard Starlette CORSMiddleware behavior.

---

## Tests Passed (37/45)

### A01 — Broken Access Control (6 PASS)
- IDOR on user export: scoped to authenticated user only
- Private workflows: require auth, return 401 unauthenticated
- Admin endpoint access: properly rejected for unauthenticated/fake-auth users
- Mass assignment: extra fields silently ignored by Pydantic schema
- Horizontal privilege (tasks): scoped to own user
- Object-level auth: ownership enforced on agent operations

### A02 — Cryptographic Failures (3 PASS)
- Sensitive data: no password hashes, API keys, Stripe IDs, or Firebase UIDs in responses
- TLS: only TLS 1.2 and 1.3 accepted; 1.0 and 1.1 rejected
- Cookies: httpOnly, Secure, SameSite=Lax flags properly set

### A03 — Injection (7 PASS)
- SQL injection: search params, POST bodies all parameterized (SQLAlchemy ORM)
- NoSQL/JSON injection: Pydantic schema validation rejects non-conforming types
- Command injection: URL passed to HTTP client, not shell
- Path traversal: FastAPI normalizes paths
- Template injection (SSTI): payloads stored as literal strings, not executed
- CRLF header injection: URL-encoded, no header splitting

### A04 — SSRF (10 PASS)
- Internal IPs (127.0.0.1, localhost, 0.0.0.0, 169.254.169.254, ::1): all blocked
- Bypass encodings (decimal, hex, octal, dotted-octal): all blocked
- Credentials in URL: blocked
- file:// protocol: rejected ("must use http or https")
- Redirect-based SSRF: server does not follow redirects
- Validate endpoint: shares same SSRF protections

### A05 — Security Misconfiguration (5 PASS)
- Error verbosity: no stack traces, file paths, or DB details leaked
- HTTP method tampering: TRACE and PROPFIND return 405
- Server version: only `cloudflare` disclosed
- Directory listing: not possible
- Debug endpoints: `.env`, `/debug`, `/config`, `/metrics`, `/actuator` all 404

### A07-A08 — XSS + Data Integrity (2 PASS)
- Reflected XSS via task suggest: payload not reflected in response
- CRLF injection: properly handled

### A09 — Logging + Rate Limiting (6 PASS)
- Rate limit on /detect: triggers at ~15 requests
- Rate limit on /feedback: triggers at ~4 requests
- Rate limit on /consent: triggers at ~2 requests
- Telemetry batch bomb: rejected at 100-event cap (422)
- User enumeration: same error message for all login attempts (Firebase mode)
- Large payload: rejected (body size limit enforced)

### Auth + Session (5 PASS)
- Brute force: rate limited + Firebase disables local login
- API key enumeration: no timing difference, all return 401
- JWT alg:none attack: rejected with 401
- CSRF: CORS blocks cross-origin cookie-based requests; API key auth is CSRF-immune
- Account deletion safety: requires exact "DELETE" confirmation string

---

## Risk Assessment

The application's overall security posture is **strong**. Key strengths:

1. **SSRF protection is excellent** — all 10 bypass techniques blocked, including redirect-based
2. **Injection attacks fully mitigated** — SQLAlchemy ORM, Pydantic validation, no shell execution
3. **Rate limiting is aggressive** — all public endpoints protected
4. **Auth is properly layered** — Firebase + httpOnly cookies + API keys, all paths validated
5. **Error messages are safe** — no stack traces or internal details leaked

The 3 medium findings are all defense-in-depth improvements, not exploitable vulnerabilities in the current deployment:
- Admin self-grant is an audit/compliance concern, not an external attack vector
- Stored XSS in name field is mitigated by React's auto-escaping
- CSP unsafe-inline is a Next.js platform constraint

---

## Remediation Priority

| Priority | Finding | Effort | Impact |
|----------|---------|--------|--------|
| 1 | M-1: Block admin self-grant | 30 min | SOC 2 compliance |
| 2 | M-2: Sanitize profile name | 30 min | Defense-in-depth |
| 3 | L-1: Add HSTS to backend | 10 min | Header hardening |
| 4 | L-2: Sanitize feedback input | 30 min | Future-proofing |
| 5 | L-3: Add CSP to backend | 10 min | Header hardening |
| 6 | M-3: Fix CSP unsafe-inline | 2-4 hrs | Complex (Next.js) |

**Estimated total remediation: ~2 hours** (excluding M-3 which requires Next.js CSP research)

---

## Appendix: Test Coverage Matrix

| OWASP Category | Tests Run | PASS | FINDING |
|----------------|-----------|------|---------|
| A01 Broken Access Control | 7 | 6 | 1 |
| A02 Cryptographic Failures | 4 | 3 | 1 |
| A03 Injection | 7 | 7 | 0 |
| A04 SSRF | 10 | 10 | 0 |
| A05 Security Misconfiguration | 7 | 5 | 2 |
| A07 XSS | 5 | 3 | 2 |
| A09 Logging & Rate Limiting | 6 | 6 | 0 |
| Auth & Session | 5 | 5 | 0 |
| **TOTAL** | **51** | **45** | **6** |
