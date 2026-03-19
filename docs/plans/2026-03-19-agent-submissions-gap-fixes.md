# Agent Submissions — Gap Fixes Plan

**Date:** 2026-03-19
**Status:** Planned
**Assessed by:** Senior Full-Stack Architect (deep codebase analysis)

---

## Summary

5 gaps identified. Core submission flow is built. These fixes make approved agents
actually usable (task dispatch, discoverability) and improve the user experience.

---

## Gaps & Solutions

### Gap 1: Agent has no endpoint (CRITICAL)
**Problem:** Approved agents have `endpoint=""` — tasks can't dispatch.
**Solution:** Langflow proxy route `POST /langflow/run/{flow_id}` that adapts A2A JSON-RPC
to Langflow REST API. Endpoint auto-set on approval using `LANGFLOW_PROXY_BASE` env var.
**Files:** New `src/api/langflow_proxy.py`, modify `src/api/admin.py`, `src/main.py`, `src/config.py`
**Effort:** 1-2 hrs

### Gap 2: No skills on approval
**Problem:** Approved agents have zero skills → invisible to search.
**Solution:** Auto-generate 1 primary skill from submission metadata with embedding.
**Files:** Modify `src/api/admin.py` (add skill creation block in approve_submission)
**Effort:** 30 min

### Gap 3: No notifications
**Problem:** Users don't know when submission status changes.
**Solution:** Phase A: localStorage-diff toast on submissions page. Phase B (later): Resend email.
**Files:** Modify `frontend/.../submissions/page.tsx`
**Effort:** 30 min (Phase A)

### Gap 4: Flow snapshot never populated
**Problem:** `flow_snapshot` column always NULL — no audit trail.
**Solution:** Fetch metadata from Langflow API at submission time (non-blocking).
**Files:** Modify `src/api/builder.py`, `src/config.py`
**Effort:** 30 min

### Gap 5: No re-submission
**Problem:** Rejected users must delete + start over, losing context.
**Solution:** `POST /builder/submissions/{id}/resubmit` updates in place, resets to pending.
**Files:** Modify `src/api/builder.py`, frontend api/hooks/UI
**Effort:** 1-2 hrs

---

## Build Sequence

Phase 1: Langflow proxy + endpoint on approval (unblocks task dispatch)
Phase 2: Skill creation on approval (unblocks discoverability)
Phase 3: Flow snapshot at submission time
Phase 4: Re-submission endpoint + UI
Phase 5: Status change notifications (localStorage toast)

---

## Security Notes

- Langflow proxy rate-limited via rate_limit_by_ip
- Proxy only serves flow_ids with approved submissions (prevents open relay)
- Embedding failure in approval is non-blocking (wrapped in try/except)
- Resubmit bypasses free-tier count (reuses existing slot)
