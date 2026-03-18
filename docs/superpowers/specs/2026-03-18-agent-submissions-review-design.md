# Agent Submissions & Review Flow — Design Spec

> **Date:** 2026-03-18
> **Status:** Approved
> **Scope:** Publish button on builder page + Admin review page for agent submissions

---

## Overview

Complete the no-code agent builder end-to-end flow: Build → Publish → Admin Review → Marketplace Listing. All backend endpoints already exist — this is frontend-only work.

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Publish UI | Fixed header button → Sheet form | Simple, always visible, no new routes |
| Admin review location | `/admin/submissions` | Consistent with existing admin section |
| Admin testing | Link to Langflow workspace | Langflow has built-in test capabilities; inline testing adds complexity |
| Notifications | Deferred | Can add later; users check submissions page for status |

---

## 1. Publish Flow (Builder Page)

### Changes to `frontend/src/app/(marketplace)/dashboard/builder/page.tsx`

Add to the builder page header:
- **"My Submissions" link** — navigates to `/dashboard/builder/submissions`
- **"Publish" button** — opens a shadcn `Sheet` (slide from right) with submission form

### Publish Sheet Form

Fields:
- `name` (required, text input, max 200 chars)
- `description` (optional, textarea)
- `category` (required, select dropdown: general, engineering, design, marketing, content, data, testing, support, business, research)
- `credits` (required, number input, min 5, default 10)
- `tags` (optional, comma-separated text input)
- `langflow_flow_id` (required, text input, with helper text "Paste your flow ID from the Langflow URL")

### Behavior
- Submit calls `POST /builder/submissions` via `useCreateSubmission()` hook (already exists)
- On success: close sheet, show toast "Submitted for review!", link to submissions page
- On 402 error (free trial limit): show toast with upgrade message
- On validation error: show field-level errors

---

## 2. Admin Review Page

### New page: `frontend/src/app/admin/submissions/page.tsx`

**Layout:** Follows existing admin page patterns (admin sidebar, heading + description, content area).

**Components:**
- Status filter dropdown (pending_review default, approved, rejected, revoked)
- Submission cards showing: name, submitter email/name, time ago, category, credits, tags, description, flow ID
- Action buttons per card based on status:
  - `pending_review`: "Test in Langflow" (external link), "Reject" (opens dialog), "Approve" (confirm dialog)
  - `approved`: "View Agent" (link), "Revoke" (confirm dialog)
  - `rejected`: shows reviewer notes (read-only)
  - `revoked`: shows revoked badge (read-only)
- Pagination (page/per_page)

### Reject Dialog
- Textarea for rejection notes (required, 1-1000 chars)
- Cancel + Confirm buttons

### Approve Confirmation
- Simple confirm dialog: "Approve this agent? It will be listed on the marketplace."
- On confirm: calls `POST /admin/submissions/{id}/approve`

### Test in Langflow
- Opens `https://builder.crewhubai.com` in new tab
- Admin can inspect and test the flow in the Langflow workspace

### Revoke Confirmation
- Confirm dialog: "Revoke this agent? It will be taken offline."
- On confirm: calls `POST /admin/submissions/{id}/revoke`

---

## 3. Admin API Client & Hooks

### New file: `frontend/src/lib/api/admin-submissions.ts`

```typescript
listSubmissions(status, page, perPage) → { submissions, total }
  GET /admin/submissions?status=&page=&per_page=

approveSubmission(id) → { status, agent_id, submission_id }
  POST /admin/submissions/{id}/approve

rejectSubmission(id, notes) → { status, submission_id }
  POST /admin/submissions/{id}/reject?notes=

revokeSubmission(id) → { status, submission_id }
  POST /admin/submissions/{id}/revoke
```

### New file: `frontend/src/lib/hooks/use-admin-submissions.ts`

```typescript
useAdminSubmissions(status, page, perPage)  // query
useApproveSubmission()                       // mutation, invalidates query
useRejectSubmission()                        // mutation, invalidates query
useRevokeSubmission()                        // mutation, invalidates query
```

---

## 4. Admin Sidebar Link

Add "Submissions" link to the admin sidebar navigation, linking to `/admin/submissions`.

---

## 5. File Inventory

### New Files
| File | Responsibility |
|------|---------------|
| `frontend/src/app/admin/submissions/page.tsx` | Admin review page |
| `frontend/src/lib/api/admin-submissions.ts` | Admin submission API client |
| `frontend/src/lib/hooks/use-admin-submissions.ts` | Admin React Query hooks |

### Modified Files
| File | Changes |
|------|---------|
| `frontend/src/app/(marketplace)/dashboard/builder/page.tsx` | Add Publish button, Sheet form, My Submissions link |
| `frontend/src/app/admin/layout.tsx` or sidebar component | Add Submissions link to admin nav |

### No Backend Changes
All endpoints already exist in `src/api/builder.py` and `src/api/admin.py`.

---

## 6. Testing

- Publish form: validates required fields, submits successfully, shows toast
- Publish form: shows 402 error when free trial limit exceeded
- Admin page: loads pending submissions, filter changes results
- Admin page: approve creates agent, card updates to approved status
- Admin page: reject requires notes, card updates to rejected with notes shown
- Admin page: "Test in Langflow" opens correct URL
- Admin page: revoke takes agent offline
- Pagination works on both user submissions and admin review pages
