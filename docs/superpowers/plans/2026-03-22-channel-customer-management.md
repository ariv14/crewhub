# Channel & Customer Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build dedicated channel management pages for developers (contacts, messages, analytics, blocking) and admins (oversight, moderation, justification-gated access) — fully SOC 2/GDPR/HIPAA compliant.

**Architecture:** Supabase single DB for all data. Inbound message text NOT stored (NULL). Outbound text encrypted (Fernet). HMAC-SHA256 pseudonymized user IDs. Admin message access requires justification + audit log. Developer notification via audit trail.

**Tech Stack:** FastAPI, SQLAlchemy (async), Alembic, Next.js, Recharts, shadcn/ui (Tabs, Sheet, Dialog, DataTable), Fernet encryption.

**Spec:** `docs/superpowers/specs/2026-03-22-channel-customer-management-design.md`

**Compliance pre-check:** SOC 2/GDPR/HIPAA review APPROVED (conditional — cross-border section added).

---

## File Map

### Backend — Migrations & Models

| File | Action | Responsibility |
|------|--------|---------------|
| `alembic/versions/036_channel_contacts_privacy.py` | Create | Contact blocks table, privacy_notice_url, message_retention_days, rename column, indexes |
| `src/models/channel.py` | Modify | Fix message_text nullable, add ChannelContactBlock model, rename platform_user_id |
| `src/models/__init__.py` | Modify | Export ChannelContactBlock |

### Backend — Schemas & API

| File | Action | Responsibility |
|------|--------|---------------|
| `src/schemas/channel.py` | Modify | Add contact, message list, admin, analytics, GDPR erasure response schemas |
| `src/api/channels.py` | Modify | Add contacts/messages/block/unblock/erasure proxy endpoints |
| `src/api/admin.py` | Modify | Add admin channels list/detail/messages with justification gate |
| `src/services/channel_service.py` | Modify | Add contacts query, message list, block/unblock, erasure, N+1 fix |

### Backend — Gateway Changes

| File | Action | Responsibility |
|------|--------|---------------|
| `demo_agents/gateway/main.py` | Modify | NULL inbound text, encrypt outbound, check blocks, fix HMAC |
| `demo_agents/gateway/message_crypto.py` | Create | Encrypt/decrypt message text (Fernet, versioned key) |

### Frontend — Developer Pages

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/app/(marketplace)/dashboard/channels/page.tsx` | Create | Channel list page |
| `frontend/src/app/(marketplace)/dashboard/channels/[id]/page.tsx` | Create | Server wrapper |
| `frontend/src/app/(marketplace)/dashboard/channels/[id]/channel-detail-client.tsx` | Create | 5-tab detail (overview, contacts, messages, analytics, settings) |
| `frontend/src/components/channels/channel-card.tsx` | Create | Reusable channel card |
| `frontend/src/components/channels/contact-table.tsx` | Create | Contacts data table |
| `frontend/src/components/channels/message-log.tsx` | Create | Message timeline |
| `frontend/src/components/channels/analytics-charts.tsx` | Create | Recharts components |
| `frontend/src/lib/hooks/use-channels.ts` | Modify | Add contacts, messages, block, analytics hooks |
| `frontend/src/lib/api/channels.ts` | Modify | Add contacts, messages, block, unblock, deleteData API functions |
| `frontend/src/types/channel.ts` | Modify | Add contact, message, analytics types |

### Frontend — Admin Pages

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/app/admin/channels/page.tsx` | Create | Admin channels list |
| `frontend/src/app/admin/channels/[id]/page.tsx` | Create | Server wrapper |
| `frontend/src/app/admin/channels/[id]/admin-channel-detail-client.tsx` | Create | Detail + justification gate |
| `frontend/src/components/channels/admin-access-gate.tsx` | Create | Justification dialog |

### Frontend — Navigation Updates

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/components/layout/user-sidebar.tsx` | Modify | Channels → /dashboard/channels |
| `frontend/src/components/layout/admin-sidebar.tsx` | Modify | Add Channels entry |
| `frontend/src/app/(marketplace)/dashboard/settings/page.tsx` | Modify | Remove Channels tab |

### Tests

| File | Action | Responsibility |
|------|--------|---------------|
| `tests/test_channel_management.py` | Create | Contact, message, block, admin, GDPR endpoints |

---

## Task 1: Migration + Model Updates

**Files:**
- Create: `alembic/versions/036_channel_contacts_privacy.py`
- Modify: `src/models/channel.py`
- Modify: `src/models/__init__.py`

- [ ] **Step 1: Create migration 036**

```python
"""Channel contacts, privacy, and performance indexes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "036"
down_revision = "035"  # or whatever is latest — check alembic/versions/

def upgrade():
    # Contact blocks table
    op.create_table(
        "channel_contact_blocks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("connection_id", UUID(as_uuid=True), sa.ForeignKey("channel_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform_user_id_hash", sa.String(200), nullable=False),
        sa.Column("blocked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("blocked_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.UniqueConstraint("connection_id", "platform_user_id_hash", name="uq_contact_blocks_conn_user"),
    )

    # Privacy notice URL
    op.add_column("channel_connections", sa.Column("privacy_notice_url", sa.String(500), nullable=True))

    # Message retention config
    op.add_column("channel_connections", sa.Column("message_retention_days", sa.Integer(), server_default="90", nullable=True))

    # Fix message_text nullable
    op.alter_column("channel_messages", "message_text", nullable=True, existing_type=sa.String(2000))

    # Rename platform_user_id → platform_user_id_hash
    op.alter_column("channel_messages", "platform_user_id", new_column_name="platform_user_id_hash")

    # Performance indexes
    op.create_index("ix_channel_messages_conn_user_created", "channel_messages",
                    ["connection_id", "platform_user_id_hash", sa.text("created_at DESC")])

def downgrade():
    op.drop_index("ix_channel_messages_conn_user_created")
    op.alter_column("channel_messages", "platform_user_id_hash", new_column_name="platform_user_id")
    op.alter_column("channel_messages", "message_text", nullable=False, existing_type=sa.String(2000))
    op.drop_column("channel_connections", "message_retention_days")
    op.drop_column("channel_connections", "privacy_notice_url")
    op.drop_table("channel_contact_blocks")
```

Check the actual latest migration revision in `alembic/versions/` before creating.

- [ ] **Step 2: Update `src/models/channel.py`**

1. Change `message_text` from `nullable=False` to `nullable=True` with `Optional[str]`
2. Rename `platform_user_id` to `platform_user_id_hash`
3. Add `privacy_notice_url` and `message_retention_days` columns to `ChannelConnection`
4. Add `ChannelContactBlock` model class:

```python
class ChannelContactBlock(Base):
    __tablename__ = "channel_contact_blocks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("channel_connections.id", ondelete="CASCADE"), nullable=False
    )
    platform_user_id_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    blocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    blocked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("connection_id", "platform_user_id_hash", name="uq_contact_blocks_conn_user"),
    )
```

- [ ] **Step 3: Export new model in `src/models/__init__.py`**

Add `from src.models.channel import ChannelContactBlock` and add to `__all__`.

- [ ] **Step 4: Verify**

Run: `python -c "from src.models import ChannelContactBlock; print('OK')"`

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/036_channel_contacts_privacy.py src/models/channel.py src/models/__init__.py
git commit -m "feat: migration 036 — contact blocks, privacy URL, message_text nullable, column rename

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Gateway Message Crypto + Privacy Changes

**Files:**
- Create: `demo_agents/gateway/message_crypto.py`
- Modify: `demo_agents/gateway/main.py`

- [ ] **Step 1: Create `message_crypto.py`**

```python
"""Encrypt/decrypt outbound message text (Fernet, versioned key)."""
import os
import base64
import hashlib
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

CURRENT_VERSION = "v1"

def _get_fernet(key: str) -> Fernet:
    derived = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))

def _get_keys() -> list[str]:
    keys = []
    primary = os.environ.get("CHANNEL_MESSAGE_KEY", "")
    if not primary:
        from config import settings
        primary = settings.gateway_service_key
        if primary:
            logger.warning("CHANNEL_MESSAGE_KEY not set — falling back to GATEWAY_SERVICE_KEY")
    if primary:
        keys.append(primary)
    old_key = os.environ.get("CHANNEL_MESSAGE_KEY_OLD", "")
    if old_key:
        keys.append(old_key)
    return keys

def encrypt_message(text: str) -> str:
    keys = _get_keys()
    if not keys:
        logger.error("No encryption key available — storing plaintext")
        return text
    return f"{CURRENT_VERSION}:{_get_fernet(keys[0]).encrypt(text.encode()).decode()}"

def decrypt_message(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    if not ciphertext.startswith(("v1:", "v2:")):
        return ciphertext  # legacy unencrypted
    _version, token = ciphertext.split(":", 1)
    for key in _get_keys():
        try:
            return _get_fernet(key).decrypt(token.encode()).decode()
        except InvalidToken:
            continue
    logger.error("Failed to decrypt message — no valid key found")
    return "[Decryption failed]"
```

- [ ] **Step 2: Update gateway `main.py`**

1. Fix `pseudonymize_user_id` to use HMAC-SHA256 (keyed):
```python
import hmac as hmac_mod

def pseudonymize_user_id(platform_user_id: str, connection_id: str) -> str:
    from config import settings
    key = f"{settings.gateway_service_key}:{connection_id}".encode()
    return hmac_mod.new(key, platform_user_id.encode(), hashlib.sha256).hexdigest()[:16]
```

2. In `process_message`, set inbound `message_text` to `None` in the log call:
```python
await client.log_message({
    ...
    "message_text": None,  # Privacy: inbound text not stored
    ...
})
```

3. In `task_callback`, encrypt outbound text before logging:
```python
from message_crypto import encrypt_message

await client.log_message({
    ...
    "message_text": encrypt_message(response_text[:2000]),
    ...
})
```

4. In `telegram_webhook`, check if user is blocked before processing:
```python
# After getting connection, before processing
connection = await client.get_connection(conn_id)
blocked_users = connection.get("blocked_users", [])
user_hash = pseudonymize_user_id(message.platform_user_id, conn_id)
if user_hash in blocked_users:
    return adapter.ack_response()  # silently drop
```

- [ ] **Step 3: Verify gateway imports**

Run: `cd demo_agents/gateway && python -c "from message_crypto import encrypt_message, decrypt_message; print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add demo_agents/gateway/message_crypto.py demo_agents/gateway/main.py
git commit -m "feat: gateway privacy — NULL inbound text, encrypt outbound, HMAC pseudonymization, block check

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Backend Schemas + Service Layer

**Files:**
- Modify: `src/schemas/channel.py`
- Modify: `src/services/channel_service.py`

- [ ] **Step 1: Add response schemas to `src/schemas/channel.py`**

Add all schemas from spec Section 4.3: `ChannelContactResponse`, `ChannelContactListResponse`, `ChannelMessageResponse`, `ChannelMessageListResponse`, `AdminChannelResponse`, `ChannelAnalyticsResponse`, `GDPRErasureResponse`.

Also add `AdminMessageAccessRequest`:
```python
class AdminMessageAccessRequest(BaseModel):
    justification: Literal["abuse_report", "developer_support", "legal_request", "compliance_check"]
```

- [ ] **Step 2: Add service methods to `src/services/channel_service.py`**

Add these methods to `ChannelService`:

1. `get_contacts(connection_id, owner_id, limit, offset)` — GROUP BY platform_user_id_hash with message count, last_seen, first_seen, LEFT JOIN channel_contact_blocks for is_blocked
2. `get_messages(connection_id, owner_id, direction, cursor, limit)` — paginated message list with cursor-based pagination
3. `block_contact(connection_id, owner_id, user_hash, blocked_by, reason)` — insert into channel_contact_blocks
4. `unblock_contact(connection_id, owner_id, user_hash)` — delete from channel_contact_blocks
5. `delete_contact_data(connection_id, owner_id, user_hash)` — GDPR erasure: delete all messages for user_hash
6. `get_blocked_users(connection_id)` — list of blocked hashes (for gateway)
7. Fix N+1: replace the loop in `list_channels` with a single batch query

Add message decryption in `get_messages`:
```python
from demo_agents.gateway.message_crypto import decrypt_message
# In message list response:
msg.message_text = decrypt_message(msg.message_text) if msg.direction == "outbound" else None
```

Note: The decrypt import needs the gateway code accessible. Alternative: copy `message_crypto.py` to `src/core/message_crypto.py` (DRY — keep one copy in `src/core/`, gateway imports from its own copy or we symlink). Better approach: just inline the same Fernet logic in a `src/core/message_crypto.py` file.

- [ ] **Step 3: Create `src/core/message_crypto.py`**

Copy the encryption/decryption logic for use by the main backend:
```python
"""Decrypt outbound message text for display. Backend-side only."""
import base64, hashlib, os, logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

def decrypt_message(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    if not ciphertext.startswith(("v1:", "v2:")):
        return ciphertext
    _version, token = ciphertext.split(":", 1)
    from src.config import settings
    keys = [k for k in [
        os.environ.get("CHANNEL_MESSAGE_KEY", ""),
        settings.gateway_service_key,
        os.environ.get("CHANNEL_MESSAGE_KEY_OLD", ""),
    ] if k]
    for key in keys:
        try:
            derived = hashlib.sha256(key.encode()).digest()
            f = Fernet(base64.urlsafe_b64encode(derived))
            return f.decrypt(token.encode()).decode()
        except InvalidToken:
            continue
    return "[Decryption failed]"
```

- [ ] **Step 4: Verify**

Run: `python -c "from src.services.channel_service import ChannelService; print('OK')"`

- [ ] **Step 5: Commit**

```bash
git add src/schemas/channel.py src/services/channel_service.py src/core/message_crypto.py
git commit -m "feat: channel contacts/messages service + message decryption + N+1 fix

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Backend API Endpoints

**Files:**
- Modify: `src/api/channels.py`
- Modify: `src/api/admin.py`
- Modify: `src/api/gateway.py`
- Modify: `src/main.py` (if needed)

- [ ] **Step 1: Add developer channel endpoints to `src/api/channels.py`**

```python
GET  /channels/{id}/contacts
GET  /channels/{id}/contacts/{user_hash}/messages
POST /channels/{id}/contacts/{user_hash}/block
DEL  /channels/{id}/contacts/{user_hash}/block
DEL  /channels/{id}/contacts/{user_hash}/messages  # GDPR erasure
GET  /channels/{id}/messages
```

All use `resolve_db_user_id` for ownership. All audit-logged.

- [ ] **Step 2: Add admin channel endpoints to `src/api/admin.py`**

```python
GET  /admin/channels/          — list all channels with owner info
GET  /admin/channels/{id}      — detail with owner info
GET  /admin/channels/{id}/messages?justification=abuse_report  — requires justification param
```

Admin message access: validate `justification` parameter, audit log with justification, create developer notification entry.

- [ ] **Step 3: Extend `GatewayConnectionResponse` in `src/api/gateway.py`**

Add `blocked_users: list[str]` to the connection response so the gateway can enforce blocks:
```python
# In the GET /gateway/connections/{id} endpoint:
blocked = await db.execute(
    select(ChannelContactBlock.platform_user_id_hash)
    .where(ChannelContactBlock.connection_id == connection_id)
)
response["blocked_users"] = [row[0] for row in blocked.all()]
```

- [ ] **Step 4: Verify all routes registered**

Run: `python -c "from src.main import app; routes = [r.path for r in app.routes if 'contact' in str(getattr(r, 'path', '')) or 'admin/channel' in str(getattr(r, 'path', ''))]; print(len(routes), routes)"`

- [ ] **Step 5: Commit**

```bash
git add src/api/channels.py src/api/admin.py src/api/gateway.py
git commit -m "feat: channel contacts/messages/block API + admin channels with justification gate

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Frontend Types + API + Hooks

**Files:**
- Modify: `frontend/src/types/channel.ts`
- Modify: `frontend/src/lib/api/channels.ts`
- Modify: `frontend/src/lib/hooks/use-channels.ts`

- [ ] **Step 1: Add types to `channel.ts`**

```typescript
export interface ChannelContact {
  platform_user_id_hash: string;
  message_count: number;
  last_seen: string;
  first_seen: string;
  is_blocked: boolean;
}

export interface ChannelMessage {
  id: string;
  direction: "inbound" | "outbound" | "system";
  platform_user_id_hash: string;
  message_text: string | null;
  credits_charged: number;
  response_time_ms: number | null;
  created_at: string;
}

export interface ChannelMessageList {
  messages: ChannelMessage[];
  cursor: string | null;
  has_more: boolean;
}

export interface ChannelContactList {
  contacts: ChannelContact[];
  total: number;
}

export interface AdminChannel extends Channel {
  owner_email: string;
  owner_name: string;
  owner_credit_balance: number;
  owner_account_tier: string;
}
```

- [ ] **Step 2: Add API functions to `channels.ts`**

```typescript
export async function getContacts(channelId: string): Promise<ChannelContactList> { ... }
export async function getContactMessages(channelId: string, userHash: string): Promise<ChannelMessageList> { ... }
export async function getChannelMessages(channelId: string, params?: { direction?: string; cursor?: string }): Promise<ChannelMessageList> { ... }
export async function blockContact(channelId: string, userHash: string, reason?: string): Promise<void> { ... }
export async function unblockContact(channelId: string, userHash: string): Promise<void> { ... }
export async function deleteContactData(channelId: string, userHash: string): Promise<{ deleted_messages: number }> { ... }
// Admin
export async function getAdminChannels(): Promise<{ channels: AdminChannel[]; total: number }> { ... }
export async function getAdminChannel(channelId: string): Promise<AdminChannel> { ... }
export async function getAdminChannelMessages(channelId: string, justification: string): Promise<ChannelMessageList> { ... }
```

- [ ] **Step 3: Add hooks to `use-channels.ts`**

```typescript
export function useContacts(channelId: string) { ... }
export function useContactMessages(channelId: string, userHash: string) { ... }
export function useChannelMessages(channelId: string, params?: {...}) { ... }
export function useBlockContact() { ... }  // mutation
export function useUnblockContact() { ... }  // mutation
export function useDeleteContactData() { ... }  // mutation
export function useAdminChannels() { ... }
export function useAdminChannel(channelId: string) { ... }
```

- [ ] **Step 4: TypeScript check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/channel.ts frontend/src/lib/api/channels.ts frontend/src/lib/hooks/use-channels.ts
git commit -m "feat: channel contacts/messages/admin types, API functions, hooks

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Shared Channel Components

**Files:**
- Create: `frontend/src/components/channels/channel-card.tsx`
- Create: `frontend/src/components/channels/contact-table.tsx`
- Create: `frontend/src/components/channels/message-log.tsx`
- Create: `frontend/src/components/channels/analytics-charts.tsx`
- Create: `frontend/src/components/channels/admin-access-gate.tsx`

- [ ] **Step 1: Create `channel-card.tsx`**

Reusable card component showing: platform icon, bot name, status badge (green active, yellow paused, red disconnected, gray pending), agent name, today's stats (messages, credits), last active time. Used in both developer and admin list pages.

- [ ] **Step 2: Create `contact-table.tsx`**

DataTable with columns: User Hash (truncated), Messages, Last Seen, Status (Active/Blocked badge). Actions: Block/Unblock button, View Messages link, Delete Data button (GDPR, with confirmation dialog).

- [ ] **Step 3: Create `message-log.tsx`**

Timeline-style message list. Each entry: direction badge (IN green / OUT blue), user hash, timestamp, message text (outbound: decrypted text, inbound: italic "[Content not stored — privacy policy]"). Load more button for cursor pagination.

- [ ] **Step 4: Create `analytics-charts.tsx`**

Recharts components: `MessageVolumeChart` (AreaChart, daily messages), `CreditBurnChart` (BarChart, daily credits), `ResponseTimeChart` (LineChart, avg response time). 7/30 day toggle. All use the `useChannelAnalytics` hook.

- [ ] **Step 5: Create `admin-access-gate.tsx`**

AlertDialog component. Title: "Access Justification Required". Description: "Admin access to channel messages is audit-logged per SOC 2 CC7.2." Dropdown with 4 options. On confirm: calls parent callback with justification string. On cancel: navigates back.

- [ ] **Step 6: TypeScript check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/channels/
git commit -m "feat: shared channel components — card, contacts, messages, charts, admin gate

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Developer Channel Pages

**Files:**
- Create: `frontend/src/app/(marketplace)/dashboard/channels/page.tsx`
- Create: `frontend/src/app/(marketplace)/dashboard/channels/[id]/page.tsx`
- Create: `frontend/src/app/(marketplace)/dashboard/channels/[id]/channel-detail-client.tsx`
- Modify: `frontend/src/components/layout/user-sidebar.tsx`
- Modify: `frontend/src/app/(marketplace)/dashboard/settings/page.tsx`

- [ ] **Step 1: Create channel list page**

`/dashboard/channels/page.tsx`: heading, stats strip (total channels, messages today, credits today), channel cards grid, "Connect a Channel" button (opens existing wizard via Sheet).

- [ ] **Step 2: Create channel detail page**

`channel-detail-client.tsx`: 5-tab layout using shadcn Tabs:
- Overview: stats grid + recent messages
- Contacts: `<ContactTable>`
- Messages: `<MessageLog>`
- Analytics: `<AnalyticsCharts>`
- Settings: budget controls, token rotation, pause/resume, delete (reuse ChannelEditSheet content inline)

- [ ] **Step 3: Update sidebar**

Change Channels href from `/dashboard/settings?tab=channels` to `/dashboard/channels`.

- [ ] **Step 4: Remove Channels tab from Settings**

Remove the Channels TabsTrigger and TabsContent from settings/page.tsx. Keep the wizard and edit sheet files (they're reused in the new pages).

- [ ] **Step 5: TypeScript check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/(marketplace)/dashboard/channels/ frontend/src/components/layout/user-sidebar.tsx frontend/src/app/(marketplace)/dashboard/settings/page.tsx
git commit -m "feat: developer channel pages — list + 5-tab detail (overview, contacts, messages, analytics, settings)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Admin Channel Pages

**Files:**
- Create: `frontend/src/app/admin/channels/page.tsx`
- Create: `frontend/src/app/admin/channels/[id]/page.tsx`
- Create: `frontend/src/app/admin/channels/[id]/admin-channel-detail-client.tsx`
- Modify: `frontend/src/components/layout/admin-sidebar.tsx`

- [ ] **Step 1: Create admin channel list page**

DataTable: platform, bot name, developer email, agent, status, messages today, credits today. Filter by platform, status. Search by bot name or developer.

- [ ] **Step 2: Create admin channel detail page**

Same 5 tabs as developer, plus:
- Developer info card at top (name, email, balance, tier)
- Messages tab: wrapped in `<AdminAccessGate>` — user must select justification before messages load
- On justification submit: store in state, pass as query param to messages API, audit log created server-side

- [ ] **Step 3: Add Channels to admin sidebar**

Add `{ href: "/admin/channels", label: "Channels", icon: Radio }` to admin sidebar nav.

- [ ] **Step 4: TypeScript check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/admin/channels/ frontend/src/components/layout/admin-sidebar.tsx
git commit -m "feat: admin channel pages — list + detail with justification-gated message access

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Compliance Polish

**Files:**
- Modify: `frontend/src/app/(marketplace)/dashboard/settings/channel-wizard.tsx`
- Modify: `frontend/src/schemas/channel.py` (if needed)

- [ ] **Step 1: Add privacy notice URL to wizard step 2**

After the credentials section, add a required URL input:
```
Label: "Privacy Notice URL"
Placeholder: "https://example.com/privacy"
Helper: "Required. Link to your privacy notice that informs users about data handling."
Validation: must be a valid URL, cannot be blank
```

Wire into the `handleSubmit` payload as `privacy_notice_url`.

- [ ] **Step 2: Add HIPAA disclaimer to wizard step 1**

Below the platform cards, add a warning banner:
```
⚠️ CrewHub channels must not be used to collect, store, or transmit Protected Health Information (PHI). No Business Associate Agreement (BAA) is in effect.
```

Style: amber border, small text, always visible.

- [ ] **Step 3: Add data residency note to wizard step 2**

Below the privacy notice URL input:
```
ℹ️ Channel data is processed and stored in the United States. If your users are in the EU, ensure your privacy notice discloses this.
```

- [ ] **Step 4: Add GDPR erasure button to contacts table**

In `contact-table.tsx`, the "Delete Data" action should show a confirmation dialog:
```
Title: "Delete User Data"
Description: "This will permanently delete all messages from this contact. This action cannot be undone."
Confirm: "Delete" (destructive)
```

On confirm: calls `useDeleteContactData` mutation.

- [ ] **Step 5: TypeScript check + commit**

```bash
git add frontend/src/
git commit -m "feat: compliance polish — privacy notice URL, HIPAA disclaimer, GDPR erasure, data residency

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Tests

**Files:**
- Create: `tests/test_channel_management.py`

- [ ] **Step 1: Schema validation tests**

Test all new schemas: `ChannelContactResponse`, `ChannelMessageResponse`, `AdminMessageAccessRequest` (valid justification, invalid justification rejected), `GDPRErasureResponse`.

- [ ] **Step 2: Import + route registration tests**

Verify all new endpoints are registered and importable.

- [ ] **Step 3: Message crypto tests**

Test `encrypt_message`, `decrypt_message`, versioned key handling, NULL passthrough, invalid key graceful failure.

- [ ] **Step 4: HMAC pseudonymization test**

Test that `pseudonymize_user_id` produces consistent hashes, different hashes for different connection_ids (per-connection isolation), and is not reversible without the key.

- [ ] **Step 5: Run all tests**

Run: `pytest tests/test_channel_management.py -v`

- [ ] **Step 6: Commit**

```bash
git add tests/test_channel_management.py
git commit -m "test: channel management — schemas, crypto, pseudonymization, routes

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Definition of Done

- [ ] Developer can view all channels at `/dashboard/channels`
- [ ] Developer can see contacts (hash, count, last seen, blocked status)
- [ ] Developer can see messages (outbound decrypted, inbound "[not stored]")
- [ ] Developer can see analytics charts (messages, credits, response time)
- [ ] Developer can block/unblock end-users (enforced at gateway)
- [ ] Developer can delete a contact's data (GDPR erasure)
- [ ] Developer privacy notice URL required in channel config
- [ ] Admin can view all channels across developers at `/admin/channels`
- [ ] Admin must provide justification before viewing messages (audit-logged)
- [ ] Developer sees admin access in their channel audit trail
- [ ] Inbound message text NOT stored (NULL)
- [ ] Outbound message text encrypted (Fernet, versioned key)
- [ ] HMAC-SHA256 keyed pseudonymization
- [ ] HIPAA disclaimer in wizard
- [ ] Data residency note in wizard
- [ ] Composite indexes for performance
- [ ] N+1 query fixed
- [ ] All tests pass
