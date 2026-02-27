# x402 Payment Integration & OpenClaw Skill Import — Design

**Date:** 2026-02-27
**Status:** Approved

## Summary

Two features that turn potential competitors into supply-side feeders:

1. **x402 payment option** — users choose `credits` or `x402` per task
2. **OpenClaw skill import** — import ClawHub/ClawMart skills as CrewHub agents with full guardrails

---

## Part 1: x402 Payment Integration

### Architecture

Receipt-verification-only approach. CrewHub verifies x402 payment receipts but never holds crypto. No custody, no regulatory risk.

### Data Model Changes

**New enum — `PaymentMethod`** (in `schemas/task.py`):
```
credits  — existing credit ledger (default)
x402     — HTTP 402 stablecoin payment
```

**Agent model** — new column:
- `accepted_payment_methods: JSON` — list of strings, default `["credits"]`

**Task model** — new columns:
- `payment_method: String(20)` — which method was used, default `"credits"`
- `x402_receipt: JSON` — verified payment proof (tx hash, chain, amount, token), nullable

**Transaction model** — new type:
- `TransactionType.X402_PAYMENT` — audit trail for verified x402 payments (no credit movement)

**New table — `x402_verified_receipts`**:
- `tx_hash: String(128)` — primary key, prevents replay attacks
- `chain: String(20)`
- `token: String(20)`
- `amount: Numeric(16,4)`
- `payer: String(128)` — wallet address
- `payee: String(128)` — recipient wallet
- `task_id: UUID` — FK to tasks
- `verified_at: DateTime`

### Config additions

```python
x402_facilitator_url: str = ""          # e.g. "https://x402.org/facilitator"
x402_supported_chains: str = "base"     # comma-separated
x402_supported_tokens: str = "USDC"     # comma-separated
x402_receipt_timeout_minutes: int = 10  # max time to submit receipt after task creation
```

### Payment Flow

1. Client creates task with `payment_method: "x402"`
2. Task broker verifies agent accepts x402 (`accepted_payment_methods` includes "x402")
3. No credit reservation. Task created with `status: pending_payment`
4. Response includes x402 payment details: amount (USDC), recipient wallet, facilitator URL
5. Client pays via x402 protocol externally
6. Client submits receipt: `POST /api/v1/tasks/{id}/x402-receipt`
7. CrewHub verifies receipt via facilitator API
8. On success: task moves to `submitted`, receipt stored, audit transaction created
9. On completion: no settlement needed (already paid)
10. On failure/cancel: no refund from CrewHub (non-custodial)

### New API Endpoints

- `POST /api/v1/tasks/{id}/x402-receipt` — submit and verify x402 payment receipt

### New Service

`src/services/x402.py` — `X402PaymentService`:
- `verify_receipt(receipt_data) -> bool` — calls facilitator API
- `check_replay(tx_hash) -> bool` — checks `x402_verified_receipts` table
- `record_receipt(task_id, receipt) -> None` — stores verified receipt

### Guardrails

| Guard | Implementation |
|-------|---------------|
| Replay protection | `x402_verified_receipts` table with unique `tx_hash` |
| Amount verification | Receipt amount >= task `credits_quoted` (converted at 1 credit = 1 USDC) |
| Chain/token validation | Reject if chain or token not in config allowlist |
| Receipt timeout | Reject if submitted > 10 min after task creation |
| Agent compatibility | Reject x402 if agent doesn't list it in `accepted_payment_methods` |

### New Task Status

Add `pending_payment` to `TaskStatus` enum — task created but waiting for x402 receipt.

---

## Part 2: OpenClaw Skill Import

### Architecture

Metadata-only import. Fetch skill manifest, extract metadata, register as a CrewHub agent. No foreign code execution.

### Import Flow

1. User calls `POST /api/v1/import/openclaw` with skill URL
2. `OpenClawImporter` fetches manifest from allowed registries
3. Parses name, description, endpoint, I/O modes
4. Validates endpoint (SSRF check), sanitizes text fields
5. Creates agent with `status: inactive`, `verification_level: unverified`
6. Stores import metadata for audit trail
7. User must explicitly activate the agent

### API Endpoint

```
POST /api/v1/import/openclaw
Body: {
  "skill_url": "https://clawhub.io/skills/my-skill",
  "pricing": { "license_type": "open", "model": "per_task", "credits": 0 },
  "category": "general",
  "tags": ["imported", "openclaw"]
}
Response: AgentResponse (status: inactive)
```

### New Service

`src/services/openclaw_importer.py` — `OpenClawImporter`:
- `import_skill(skill_url, pricing, category, tags, owner_id) -> Agent`
- `_fetch_manifest(url) -> dict` — HTTP GET with size limit
- `_parse_manifest(raw) -> dict` — extract structured data
- `_sanitize_text(text) -> str` — strip HTML/scripts
- `_check_duplicate(endpoint_url) -> bool`

### Schema Changes

**Agent model** — new column:
- `metadata: JSON` — default `{}`, stores `source`, `source_url`, `imported_at`

**New schema** — `OpenClawImportRequest`:
- `skill_url: str` — the ClawHub/ClawMart URL
- `pricing: PricingModel` — required (OpenClaw has no pricing equivalent)
- `category: str = "general"`
- `tags: list[str] = []`

### Guardrails

| Guard | Implementation |
|-------|---------------|
| URL allowlist | Only fetch from `clawhub.io`, `github.com/openclaw/*`, `clawmart.online` |
| Content size limit | Max 100KB manifest response |
| Endpoint SSRF check | Reuse `_validate_public_url()` from `schemas/agent.py` |
| Mandatory inactive start | Imported agents always start `inactive` + `unverified` |
| Import rate limit | Max 10 imports per user per hour (in-memory counter) |
| Text sanitization | Strip HTML tags, script content from all text fields |
| Duplicate detection | Check existing agents for same endpoint URL |
| Source tracking | `metadata.source = "openclaw"`, `metadata.source_url`, `metadata.imported_at` |

### What We Don't Do

- No code execution — never run OpenClaw skill code
- No automatic trust — imported skills start unverified
- No payment bridging — if OpenClaw skill expects x402, user configures x402 on their task
- No automatic sync — import is one-time snapshot, re-import for updates

---

## Files to Create/Modify

### New Files
- `src/services/x402.py` — x402 payment verification service
- `src/services/openclaw_importer.py` — OpenClaw skill import service
- `src/api/imports.py` — import API endpoints
- `src/models/x402_receipt.py` — verified receipt model
- `src/schemas/x402.py` — x402 request/response schemas
- `src/schemas/imports.py` — import request schemas

### Modified Files
- `src/models/agent.py` — add `accepted_payment_methods`, `metadata` columns
- `src/models/task.py` — add `payment_method`, `x402_receipt` columns
- `src/models/transaction.py` — add `X402_PAYMENT` type
- `src/schemas/task.py` — add `PaymentMethod` enum, update `TaskCreate`
- `src/schemas/agent.py` — add `accepted_payment_methods` to create/update/response
- `src/services/task_broker.py` — handle x402 payment path in `create_task`
- `src/config.py` — add x402 settings
- `src/main.py` — register import router
- `src/core/exceptions.py` — add `PaymentVerificationError`
- `alembic/versions/001_initial_schema.py` — add new columns and table
- `.env.example` — add x402 config vars
