# Channel & Customer Management — Design Spec

> **Date:** 2026-03-22
> **Status:** Draft (v2 — post-review)
> **Scope:** Admin channel oversight + Developer channel management with contacts, messages, analytics
> **Reviewed by:** Architect, Compliance Head, Platform Lead
> **Review fixes:** 3 critical (migration safety, phase ordering, encryption keys) + 5 important resolved

---

## Overview

Dedicated channel management pages for both admins and developers. Developers manage their bot's end-users (contacts, messages, analytics, blocking). Admins oversee all channels across developers with moderation and compliance controls.

**Key architectural decision:** All data stays in **Supabase** (single database). Inbound message text is NOT stored (NULL). Outbound message text is encrypted (Fernet). This keeps storage within the 500MB free tier (~416MB projected at 10K msgs/day × 90 days).

---

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Page structure | Hybrid — sidebar list + detail pages | Matches existing My Agents → Agent Detail pattern |
| Message storage | **Supabase** (same database as everything else) | Simplest — one DB, one connection, SOC 2 certified, encryption at rest included |
| Inbound message text | **NULL** (not stored) | Privacy by design (GDPR Art. 25), saves ~80% storage |
| Outbound message text | **Encrypted (Fernet)** | Developer needs to debug agent responses |
| Contacts table | No — derive from message aggregation | Lighter, no sync issues. Only `channel_contact_blocks` table for blocking. |
| Blocking | `channel_contact_blocks` table in Supabase | Enforced at gateway webhook handler level |
| Admin message access | **Justification-gated** + audit-logged + developer notified | GDPR processor compliance, SOC 2 CC7.2 |
| HIPAA | Disclaimer: no PHI without BAA | Block healthcare use without proper agreement |
| Pseudonymization | **HMAC-SHA256** (keyed, not plain SHA-256) | Per-connection key derivation prevents cross-channel correlation |

---

## 1. Storage Architecture

### Single Supabase Database (500MB free tier)

```
Core data (~50MB):
  users, agents, tasks, transactions, workflows, audit_logs

Channel config (~5MB):
  channel_connections (tokens encrypted, privacy_notice_url required)

Channel messages (~360MB max at 10K msgs/day × 90 days):
  channel_messages
    - inbound: message_text = NULL (not stored)
    - outbound: message_text = encrypted Fernet ciphertext
    - platform_user_id_hash: HMAC-SHA256 pseudonymized
  channel_contact_blocks (~1MB)

Total projected: ~416MB (fits 500MB free tier)
```

### Storage Budget

```
Per message row (metadata only, no inbound text):
  UUID fields (id, connection_id, task_id): 3 × 36 = 108 bytes
  platform_user_id_hash: 16 bytes
  platform_message_id: ~30 bytes
  direction + media_type: ~15 bytes
  credits_charged + response_time_ms: 12 bytes
  timestamps: 16 bytes
  outbound encrypted text (50% of rows): ~500 bytes avg
  ≈ 400 bytes avg per row

10K msgs/day × 400 bytes × 90 days = ~360MB
With indexes: ~420MB total
```

---

## 2. Data Model Changes

### 2.1 New Migration: `036_channel_contacts_and_privacy.py`

```sql
-- Contact blocks table
CREATE TABLE channel_contact_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES channel_connections(id) ON DELETE CASCADE,
    platform_user_id_hash VARCHAR(200) NOT NULL,
    blocked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    blocked_by UUID REFERENCES users(id),
    reason VARCHAR(200),
    UNIQUE(connection_id, platform_user_id_hash)
);

-- Privacy notice URL (GDPR requirement)
ALTER TABLE channel_connections ADD COLUMN privacy_notice_url VARCHAR(500);

-- Message retention config (per-channel, default 90 days)
ALTER TABLE channel_connections ADD COLUMN message_retention_days INTEGER DEFAULT 90;

-- Performance index for contacts aggregation
CREATE INDEX ix_channel_messages_conn_user_created
  ON channel_messages(connection_id, platform_user_id, created_at DESC);
```

### 2.2 Modify `channel_messages` table behavior

No schema change needed — the existing `message_text String(2000)` column stays. The change is in the **gateway logic**:
- Inbound: set `message_text = NULL` (column is already nullable in the schema, but current model has `nullable=False` — fix this)
- Outbound: set `message_text = encrypt_value(response_text)`

Fix in `src/models/channel.py`:
```python
# Change from:
message_text: Mapped[str] = mapped_column(String(2000), nullable=False)
# To:
message_text: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
```

### 2.3 Rename `platform_user_id` to `platform_user_id_hash`

For clarity (both in `channel_messages` and `channel_contact_blocks`), rename the column to make it obvious this is a hash, not a raw ID. Add to migration 036:
```sql
ALTER TABLE channel_messages RENAME COLUMN platform_user_id TO platform_user_id_hash;
```

### 2.4 Fix pseudonymization: SHA-256 → HMAC-SHA256

The current gateway `pseudonymize_user_id()` uses plain `hashlib.sha256()` which is not keyed — anyone with the `connection_id` can brute-force Telegram user IDs (sequential integers).

Fix in `demo_agents/gateway/main.py`:
```python
import hmac

def pseudonymize_user_id(platform_user_id: str, connection_id: str) -> str:
    """HMAC-SHA256 pseudonymization with gateway service key."""
    key = f"{settings.gateway_service_key}:{connection_id}".encode()
    return hmac.new(key, platform_user_id.encode(), hashlib.sha256).hexdigest()[:16]
```

---

## 3. Encryption Architecture

### 3.1 Message Text Encryption

**Key source:** Dedicated `CHANNEL_MESSAGE_KEY` environment variable on the gateway. Falls back to `GATEWAY_SERVICE_KEY` if not set (with a warning log).

**Encryption flow (outbound messages only):**
```python
from cryptography.fernet import Fernet
import base64, hashlib

def get_message_fernet() -> Fernet:
    key = os.environ.get("CHANNEL_MESSAGE_KEY", settings.gateway_service_key)
    # Derive a valid Fernet key from the secret
    derived = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))

def encrypt_message(text: str) -> str:
    return f"v1:{get_message_fernet().encrypt(text.encode()).decode()}"

def decrypt_message(ciphertext: str) -> str:
    if ciphertext.startswith("v1:"):
        return get_message_fernet().decrypt(ciphertext[3:].encode()).decode()
    return ciphertext  # legacy unencrypted (shouldn't exist)
```

**Where decryption happens:** At the main backend proxy layer (`src/api/channels.py`) when serving message list to developer/admin. Gateway stores encrypted, never decrypts.

**Key rotation:** Change `CHANNEL_MESSAGE_KEY`, update version prefix to `v2:`. Old messages with `v1:` prefix still decrypt with old key (dual-key support via env var `CHANNEL_MESSAGE_KEY_OLD`).

---

## 4. API Endpoints

### 4.1 Developer-Facing (add to `src/api/channels.py`)

```
GET  /channels/{id}/contacts                          — aggregated contact stats
GET  /channels/{id}/contacts/{user_hash}/messages      — per-user message thread
POST /channels/{id}/contacts/{user_hash}/block         — block end-user
DEL  /channels/{id}/contacts/{user_hash}/block         — unblock end-user
DEL  /channels/{id}/contacts/{user_hash}/messages      — GDPR erasure
GET  /channels/{id}/messages?direction=&cursor=&limit= — paginated message log
```

All require `resolve_db_user_id` (ownership check).

### 4.2 Admin-Facing (add to `src/api/admin.py`)

```
GET  /admin/channels/                     — all channels, all developers
GET  /admin/channels/{id}                 — channel detail with developer info
GET  /admin/channels/{id}/messages        — requires justification parameter
```

Admin endpoints reuse the same service methods but bypass ownership check via `require_admin`. Message access requires `justification` query parameter (one of: `abuse_report`, `developer_support`, `legal_request`, `compliance_check`).

### 4.3 Response Schemas (add to `src/schemas/channel.py`)

```python
class ChannelContactResponse(BaseModel):
    platform_user_id_hash: str
    message_count: int
    last_seen: datetime
    first_seen: datetime
    is_blocked: bool = False

class ChannelContactListResponse(BaseModel):
    contacts: list[ChannelContactResponse]
    total: int

class ChannelMessageResponse(BaseModel):
    id: UUID
    direction: str  # inbound | outbound
    platform_user_id_hash: str
    message_text: str | None  # NULL for inbound, decrypted for outbound
    credits_charged: float
    response_time_ms: int | None
    created_at: datetime

class ChannelMessageListResponse(BaseModel):
    messages: list[ChannelMessageResponse]
    cursor: str | None  # for next page
    has_more: bool

class AdminChannelResponse(ChannelResponse):
    owner_email: str
    owner_name: str
    owner_credit_balance: float
    owner_account_tier: str

class ChannelAnalyticsResponse(BaseModel):
    daily: list[dict]  # [{date, messages, credits, avg_response_ms}]
    total_messages: int
    total_credits: float
    avg_response_ms: float | None

class GDPRErasureResponse(BaseModel):
    deleted_messages: int
    user_hash: str
    channel_id: UUID
```

---

## 5. Frontend Pages

### 5.1 Developer: `/dashboard/channels` (List Page)

Move out of Settings tab. Dedicated page:
- Channel cards: platform icon, bot name, status badge, agent, today's stats
- "Connect a Channel" button (opens existing wizard)
- Quick actions: pause/resume, configure
- Stats strip: total channels, messages today, credits today

### 5.2 Developer: `/dashboard/channels/[id]` (Detail Page)

5-tab detail page:

**Overview:** Status card, stats grid (messages today, active contacts, credits used, avg response time), recent activity (last 10 messages compact)

**Contacts:** Table with user_hash (truncated), message count, last seen, status. Actions: block/unblock, view messages, delete data (GDPR). Blocked section collapsed.

**Messages:** Chronological log. Inbound: "[Content not stored]" placeholder. Outbound: decrypted agent response. Filter by direction, date range. Cursor pagination.

**Analytics:** Daily charts (messages, credits, response time) with 7/30 day toggle. Top contacts table.

**Settings:** Config display, budget controls, token rotation, pause/resume, delete channel.

### 5.3 Admin: `/admin/channels` (List Page)

All channels across developers. Table with platform, bot name, developer email, agent, status, messages/credits today. Filter by platform, status, developer. Search.

### 5.4 Admin: `/admin/channels/[id]` (Detail Page)

Same 5 tabs as developer, plus:

**Developer Info card** at top: name, email, balance, tier, total channels.

**Message Access Gate (COMPLIANCE — P0):**
Before Messages tab loads, admin selects justification from dropdown:
- "Abuse report investigation"
- "Developer-requested support"
- "Legal/regulatory request"
- "Platform compliance check"

Selection is audit-logged. Developer sees entry in their channel's audit trail (visible in Settings tab): "Admin viewed messages on [date]. Reason: [justification]"

---

## 6. Frontend File Structure

```
# Developer pages (new)
app/(marketplace)/dashboard/channels/
  page.tsx                              — channel list
  [id]/
    page.tsx                            — server wrapper
    channel-detail-client.tsx           — 5-tab detail

# Admin pages (new)
app/admin/channels/
  page.tsx                              — all channels list
  [id]/
    page.tsx                            — server wrapper
    admin-channel-detail-client.tsx     — detail + justification gate

# Shared components (new)
components/channels/
  channel-card.tsx                      — reusable card
  contact-table.tsx                     — contacts data table
  message-log.tsx                       — message timeline
  analytics-charts.tsx                  — chart components
  admin-access-gate.tsx                 — justification dialog

# New hooks + API (add to existing)
lib/hooks/use-channels.ts              — add: useContacts, useMessages, useBlockContact, useChannelAnalytics
lib/api/channels.ts                    — add: getContacts, getMessages, blockContact, unblockContact, deleteContactData

# Existing files to modify
components/layout/user-sidebar.tsx      — Channels href → /dashboard/channels
components/layout/admin-sidebar.tsx     — add Channels entry
settings/page.tsx                       — remove Channels tab
settings/channels-tab.tsx              — DELETE (replaced)
```

---

## 7. Compliance Requirements

### P0 — Must ship with feature

| # | Requirement | Implementation |
|---|------------|----------------|
| 1 | Admin message justification gate | Dropdown before Messages tab, audit-logged |
| 2 | HIPAA disclaimer | Wizard step 1: "No PHI without BAA" warning |
| 3 | Privacy notice URL | Required field in channel config (`privacy_notice_url`), validated as URL |
| 4 | Right to erasure | `DEL /channels/{id}/contacts/{hash}/messages` + UI button |
| 5 | Audit logging | All admin + developer message/contact access logged |
| 6 | Inbound text not stored | Gateway sets `message_text = NULL` for inbound |
| 7 | Outbound text encrypted | Fernet with versioned key (`v1:` prefix) |
| 8 | HMAC pseudonymization | Keyed HMAC-SHA256 (not plain SHA-256) |

### P1 — Within 30 days

| # | Requirement | Implementation |
|---|------------|----------------|
| 9 | DPA update | Cover channel messages as processing activity |
| 10 | Configurable retention | `message_retention_days` per channel (default 90) |
| 11 | Admin role scoping | "compliance_officer" role for message access |

---

## 8. Performance Optimizations

| Concern | Solution |
|---------|----------|
| N+1 query on channel list | Batch query: `SELECT connection_id, COUNT(*), SUM(credits_charged) FROM channel_messages WHERE created_at >= today GROUP BY connection_id` |
| Contacts aggregation | Composite index: `(connection_id, platform_user_id_hash, created_at DESC)` |
| Message list pagination | Cursor-based using `(created_at, id)` compound cursor |
| Analytics charts | `GROUP BY date` with index on `(connection_id, created_at)` |
| Outbound text decryption | On-demand per page (20 messages × ~1ms = 20ms) |

---

## 9. Phase Ordering (Critical — from review)

**Phase A must be sequential, not parallel:**

1. Fix `channel_messages.message_text` to `nullable=True` (model + migration)
2. Add `privacy_notice_url` and `message_retention_days` to `channel_connections`
3. Create `channel_contact_blocks` table
4. Fix pseudonymization (SHA-256 → HMAC-SHA256)
5. Update gateway to store NULL inbound text + encrypt outbound text
6. Disable old `POST /gateway/log-message` plaintext path
7. Add new channel proxy endpoints + admin endpoints
8. Build frontend pages

**The old log-message endpoint must be updated (not removed)** to accept the new format. The gateway already calls it — just change what it sends.

---

## 10. Implementation Phases

### Phase A: Backend Data + API (3-4 days)
- Migration 036 (contact_blocks, privacy_notice_url, retention, indexes, rename column)
- Fix message_text nullable, HMAC pseudonymization
- Gateway: NULL inbound text, encrypt outbound text
- Proxy endpoints for contacts/messages
- Admin channel endpoints with justification gate
- Response schemas
- N+1 query fix
- Audit logging on all access

### Phase B: Developer Frontend (2-3 days)
- `/dashboard/channels` list page
- `/dashboard/channels/[id]` detail with 5 tabs
- Move wizard + edit sheet from Settings
- Update sidebar, remove Settings tab
- Hooks + API client additions

### Phase C: Admin Frontend (1-2 days)
- `/admin/channels` list page
- `/admin/channels/[id]` detail with justification gate
- Admin sidebar entry

### Phase D: Compliance Polish (1 day)
- Privacy notice URL in wizard
- HIPAA disclaimer
- GDPR erasure button
- Developer notification on admin access

---

## 11. Definition of Done

- [ ] Developer can view all channels at `/dashboard/channels`
- [ ] Developer can see contacts, messages (outbound decrypted, inbound "[not stored]"), analytics per channel
- [ ] Developer can block/unblock end-users (enforced at gateway)
- [ ] Developer can delete a contact's data (GDPR erasure)
- [ ] Admin can view all channels across developers
- [ ] Admin must provide justification before viewing messages (audit-logged)
- [ ] Developer sees admin access in their channel audit trail
- [ ] Inbound message text NOT stored (NULL)
- [ ] Outbound message text encrypted (Fernet, versioned key)
- [ ] platform_user_id pseudonymized with HMAC-SHA256 (keyed)
- [ ] 90-day auto-purge running
- [ ] HIPAA disclaimer in wizard
- [ ] Privacy notice URL required in channel config
- [ ] Composite indexes for contacts/messages performance
- [ ] N+1 query fixed (batch stats query)
- [ ] All data in Supabase (no separate database)
- [ ] All tests pass
