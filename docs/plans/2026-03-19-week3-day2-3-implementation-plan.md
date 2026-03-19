# Week 3 Day 2-3: Final 7 Compliance Items — Implementation Plan

**Date:** 2026-03-19
**Status:** Planned
**Assessed by:** Security Architect + Code Architect (deep codebase analysis)

---

## Summary

7 MEDIUM items remaining. All are feature additions (no exploitable vulnerabilities).
After completion: 64/64 findings resolved (100%).

---

## Build Sequence (5 Phases)

### Phase A: Database Migrations (no service impact)

**Migration 031:** `alembic/versions/031_gdpr_compliance.py`
```sql
ALTER TABLE users ADD COLUMN deletion_requested_at TIMESTAMP WITH TIME ZONE NULL;
ALTER TABLE users ADD COLUMN consent_version VARCHAR(20) NULL;
ALTER TABLE users ADD COLUMN consent_given_at TIMESTAMP WITH TIME ZONE NULL;
ALTER TABLE users ADD COLUMN consent_ip VARCHAR(45) NULL;
```

**Migration 032:** `alembic/versions/032_admin_roles.py`
```sql
ALTER TABLE users ADD COLUMN admin_role VARCHAR(20) NULL;
UPDATE users SET admin_role = 'super_admin' WHERE is_admin = TRUE;
```

**Model changes:** `src/models/user.py` — add 5 columns

### Phase B: Encryption Hardening (backward-compatible)

**Rewrite** `src/core/encryption.py`:
- Version-prefixed ciphertext: `v1:<fernet_token>`
- Legacy bare tokens decrypt via fallback path
- New `ENCRYPTION_KEY` env var (falls back to SECRET_KEY)

**Add** `encryption_key` to `src/config.py`
**Create** `scripts/reencrypt_llm_keys.py`

### Phase C: GDPR Endpoints

**`GET /auth/me/export`** — rate-limited (2/hr), returns JSON with:
- profile, api_key_metadata, llm_key_providers, credit_balance, consent
- agents, tasks (cap 500), transactions (cap 1000), workflows, runs (cap 200)
- Never includes: hashed_password, api_key_hash, raw llm_api_keys

**`DELETE /auth/me`** — requires `{"confirmation": "DELETE"}` body:
- Immediate PII scrub: email→hash, name→"Deleted User", keys→null, Stripe IDs→null
- Sets `deletion_requested_at`, `is_active=False`
- Nulls task messages/artifacts for owned tasks
- Fire-and-forget Firebase `delete_user(uid)`
- Clears httpOnly session cookie

**Consent recording** — on new user creation in `/auth/firebase`, `/auth/session`, `/auth/register`:
- Sets `consent_version`, `consent_given_at`, `consent_ip`

### Phase D: Admin RBAC

**Roles:** `super_admin` (all), `ops_admin` (agents/submissions/stats), `billing_admin` (transactions/credits)

**New dependencies:** `require_ops_or_super`, `require_billing_or_super`
**New endpoint:** `PUT /admin/users/{id}/role`
**Bootstrap:** sets `admin_role = "super_admin"` on bootstrapped user

### Phase E: Frontend

**Settings page — Danger Zone card (Profile tab):**
- "Download Your Data" button → calls `/auth/me/export`, triggers file download
- "Delete Account" button → confirmation dialog ("type DELETE"), calls `DELETE /auth/me`, logs out

**api-client.ts:** extend `delete()` to accept optional body
**get-auth-token.ts:** centralized token read (Phase 2 prep for localStorage removal)
**SSE hooks:** use `getAuthToken()` instead of inline localStorage

---

## Files to Create/Modify

| File | Action |
|---|---|
| `alembic/versions/031_gdpr_compliance.py` | Create |
| `alembic/versions/032_admin_roles.py` | Create |
| `src/models/user.py` | Modify (5 columns) |
| `src/schemas/auth.py` | Modify (add admin_role, consent to UserResponse) |
| `src/core/encryption.py` | Rewrite (version-prefix) |
| `src/config.py` | Modify (encryption_key, consent_version) |
| `src/core/rate_limiter.py` | Modify (export limiter) |
| `src/api/auth.py` | Modify (export, delete, consent) |
| `src/api/admin.py` | Modify (RBAC guards, role endpoint) |
| `src/tasks/gdpr_purge.py` | Create |
| `scripts/reencrypt_llm_keys.py` | Create |
| `frontend/src/lib/api-client.ts` | Modify (delete body) |
| `frontend/src/lib/api/auth.ts` | Modify (export, delete functions) |
| `frontend/src/lib/get-auth-token.ts` | Create |
| `frontend/src/lib/hooks/use-agent-activity.tsx` | Modify |
| `frontend/src/lib/hooks/use-activity-feed.ts` | Modify |
| `frontend/src/app/(marketplace)/dashboard/settings/page.tsx` | Modify (Danger Zone) |

---

## Risks

- Migration 032 backfill: existing admins have `admin_role=NULL` during deploy window → handle NULL as super_admin
- Export endpoint timeout: cap queries, add 25s asyncio timeout
- DELETE /auth/me Firebase call: use asyncio.to_thread, fire-and-forget
- Encryption backward compat: bare tokens (no prefix) must still decrypt
- Agent `did_private_key_encrypted` also uses encryption.py — verify same path
