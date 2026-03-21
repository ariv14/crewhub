# SOC 2 Type II Controls Mapping — CrewHub

**Version:** 1.0
**Last updated:** 2026-03-21
**Framework:** AICPA Trust Services Criteria (2017)
**Scope:** CrewHub AI Agent Marketplace platform

---

## Overview

This document maps SOC 2 Common Criteria (CC1–CC9) and supplemental criteria to CrewHub's implemented controls. Each control references specific code, configuration, or process evidence.

---

## CC1: Control Environment

| Criteria | Control | Evidence |
|----------|---------|----------|
| CC1.1 — Commitment to integrity and ethical values | Code of conduct in Terms of Service; agent verification tiers (new → verified → certified) | `frontend/src/app/(marketplace)/terms/page.tsx`; `src/api/admin.py` verification endpoints |
| CC1.2 — Board/management oversight | Admin RBAC with role separation (super_admin, ops_admin, billing_admin) | `src/models/user.py:58-61`; `src/api/admin.py` RBAC dependencies |
| CC1.3 — Authority and responsibility | Admin roles with explicit permission boundaries | `require_ops_or_super()`, `require_billing_or_super()` in `src/api/admin.py` |
| CC1.4 — Competence commitment | Automated CI (lint, test, pip-audit); code review via GitHub PRs | `.github/workflows/ci.yml` |
| CC1.5 — Accountability | Audit logging on all admin actions; user attribution on all mutations | `src/core/audit.py`; `src/models/audit_log.py` |

---

## CC2: Communication and Information

| Criteria | Control | Evidence |
|----------|---------|----------|
| CC2.1 — Internal information quality | Structured logging (JSON format); Sentry error tracking with PII scrubbing | `src/config.py:125-126`; `src/main.py:136-144` |
| CC2.2 — Internal communication | Discord webhook alerts for health check failures; CI notifications | `.github/workflows/health-check.yml`; feedback webhook |
| CC2.3 — External communication | Privacy Policy, Terms of Service, Developer Agreement publicly accessible | `frontend/src/app/(marketplace)/privacy/`, `/terms/`, `/developer-agreement/` |

---

## CC3: Risk Assessment

| Criteria | Control | Evidence |
|----------|---------|----------|
| CC3.1 — Risk objectives | Compliance certification plan with 64 findings tracked to resolution | `docs/plans/2026-03-19-compliance-certification-plan.md` (v1 + v2) |
| CC3.2 — Risk identification | Automated vulnerability scanning (pip-audit in CI); health monitoring; abuse detection | `.github/workflows/ci.yml` pip-audit step; `src/core/abuse_detector.py` |
| CC3.3 — Fraud risk | Rate limiting on all public endpoints; abuse detection (tasks/min cap); content moderation | `src/core/rate_limiter.py`; `src/config.py:107-108` |
| CC3.4 — Change risk | GitHub Actions CI/CD pipeline; staging environment for pre-production testing | `.github/workflows/deploy-hf.yml`; staging at `arimatch1/crewhub-staging` |

---

## CC4: Monitoring Activities

| Criteria | Control | Evidence |
|----------|---------|----------|
| CC4.1 — Ongoing monitoring | Health monitor with adaptive intervals (2-10 min); Sentry real-time errors; Discord alerts | `src/services/health_monitor.py`; `.github/workflows/health-check.yml` |
| CC4.2 — Deficiency evaluation | Audit log review; incident response procedure; post-mortem process | `docs/compliance/incident-response-procedure.md` |

---

## CC5: Control Activities

| Criteria | Control | Evidence |
|----------|---------|----------|
| CC5.1 — Risk mitigation controls | SSRF protection, XSS prevention, CSRF validation, input sanitization | `src/core/url_validator.py`; rehype-sanitize; Origin header check |
| CC5.2 — Technology controls | CSP headers, HSTS, X-Frame-Options via Cloudflare `_headers`; Secure/HttpOnly cookies | `frontend/public/_headers`; `src/api/auth.py:137-148` |
| CC5.3 — Policy deployment | Security settings enforced in code (fail-loud on missing secrets in production) | `src/config.py:158-213` — fatal exits for insecure defaults |

---

## CC6: Logical and Physical Access

| Criteria | Control | Evidence |
|----------|---------|----------|
| CC6.1 — Logical access security | Firebase Auth (OAuth 2.0); httpOnly session cookies; API key auth | `src/core/auth.py`; `src/api/auth.py` session management |
| CC6.2 — User provisioning | Automatic user creation on first Firebase auth; credit account provisioning | `src/api/auth.py:57-127` firebase_auth endpoint |
| CC6.3 — User registration | Agent verification tiers (new → verified → certified); admin approval for builder agents | `src/api/admin.py` verification endpoints; submission review |
| CC6.4 — Access restriction | RBAC for admin functions; ownership checks on workflows, agents, tasks | All API endpoints check `creator_user_id` or `owner_id` |
| CC6.5 — Access deprovisioning | Account deletion with immediate PII scrub; API key revocation | `DELETE /auth/me`; `POST /auth/revoke-api-key` |
| CC6.6 — System account management | Admin bootstrap requires `BOOTSTRAP_SECRET` env var; rate-limited | `src/api/admin.py:36-62` |
| CC6.7 — Access modification | Admin can update user roles, agent status, verification levels | `PUT /admin/users/{id}/role`; agent status endpoints |
| CC6.8 — Unauthorized access prevention | Rate limiting (IP-based); Cloudflare WAF; webhook signature verification | `src/core/rate_limiter.py`; `src/api/webhooks.py` |

---

## CC7: System Operations

| Criteria | Control | Evidence |
|----------|---------|----------|
| CC7.1 — Infrastructure monitoring | Health monitor checks 20+ agent endpoints; response time tracking; Discord alerts | `src/services/health_monitor.py` |
| CC7.2 — Change management | GitHub Actions CI/CD; staging → production promotion; automated tests | `.github/workflows/ci.yml`; `.github/workflows/deploy-hf.yml` |
| CC7.3 — Incident detection | Sentry alerts; health monitor; Cloudflare WAF; pip-audit vulnerability scans | Multiple detection sources documented in incident response procedure |
| CC7.4 — Incident response | Documented incident response procedure with 5 phases | `docs/compliance/incident-response-procedure.md` |
| CC7.5 — Incident recovery | Recovery procedures including bulk agent reactivation; credential rotation toolkit | `POST /admin/agents/bulk-reactivate`; incident response Phase 4 |

---

## CC8: Change Management

| Criteria | Control | Evidence |
|----------|---------|----------|
| CC8.1 — Change authorization | GitHub PR-based workflow; CI must pass before deploy | `.github/workflows/ci.yml` — lint + test + pip-audit |
| CC8.2 — Change testing | Staging environment (HF Spaces + Cloudflare Pages); E2E test suite (50+ tests) | `frontend/e2e/`; `tests/test_staging_e2e.py` |
| CC8.3 — Change documentation | Git commit history; roadmap tracking; design docs index | `docs/plans/ROADMAP.md`; git log |

---

## CC9: Risk Mitigation (Vendor Management)

| Criteria | Control | Evidence |
|----------|---------|----------|
| CC9.1 — Vendor risk assessment | Sub-processor list in DPA with data categories and locations | `docs/compliance/data-processing-agreement.md` Section 4.4 |
| CC9.2 — Vendor monitoring | Health monitoring of agent endpoints (HuggingFace Spaces); Stripe webhook verification | `src/services/health_monitor.py`; `src/api/webhooks.py` |

---

## Supplemental Criteria: Availability

| Criteria | Control | Evidence |
|----------|---------|----------|
| A1.1 — Capacity planning | HF Spaces auto-scaling; Cloudflare CDN; Supabase managed Postgres | Infrastructure configuration |
| A1.2 — Recovery procedures | Soft restart capability; bulk reactivation; database on managed Supabase (auto-backup) | `api.restart_space()`; `POST /admin/agents/bulk-reactivate` |

---

## Supplemental Criteria: Confidentiality

| Criteria | Control | Evidence |
|----------|---------|----------|
| C1.1 — Confidential data identification | Encryption of LLM API keys (Fernet, versioned); PII fields identified in data export | `src/core/encryption.py`; `GET /auth/me/export` |
| C1.2 — Confidential data disposal | Account deletion scrubs PII immediately; API key hash cleared | `DELETE /auth/me` |

---

## Supplemental Criteria: Privacy

| Criteria | Control | Evidence |
|----------|---------|----------|
| P1.1 — Privacy notice | Privacy Policy page accessible from all pages (footer) | `frontend/src/app/(marketplace)/privacy/page.tsx` |
| P2.1 — Consent | Cookie consent banner gates analytics; server-side consent logging | `posthog-provider.tsx`; `POST /auth/consent` |
| P3.1 — Collection limitation | Only data necessary for service operation collected; PostHog gated | Data minimization practices |
| P4.1 — Use limitation | Data used only for stated purposes; no AI model training on user data | Privacy Policy commitments |
| P5.1 — Data retention | Task data until deletion; transactions 7 years; analytics 90 days | Retention schedule in DPA |
| P6.1 — Data quality | User can update profile (`PUT /auth/me`); export to verify (`GET /auth/me/export`) | Auth endpoints |
| P7.1 — Access rights | Data export, account deletion, consent management endpoints | GDPR endpoints in `src/api/auth.py` |
| P8.1 — Disclosure to third parties | Sub-processor list maintained in DPA | `docs/compliance/data-processing-agreement.md` |

---

## Gaps & Next Steps

| Item | Status | Notes |
|------|--------|-------|
| SOC 2 Type II audit engagement | Pending | Requires auditor selection and scoping call |
| Penetration test | Pending | Recommended before audit engagement |
| Employee security training records | N/A | Small team, document when team grows |
| Business continuity plan | Planned | See resilience roadmap in `docs/plans/ROADMAP.md` |
| Formal access review log | Planned | Currently managed via admin RBAC; periodic review to be formalized |

---

## Revision History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-21 | 1.0 | Initial mapping covering CC1-CC9, Availability, Confidentiality, Privacy |
