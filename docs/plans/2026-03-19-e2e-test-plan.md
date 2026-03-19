# CrewHub E2E Test Plan — Frontend-to-Backend

**Date:** 2026-03-19
**Purpose:** Phase-by-phase UI/UX testing with exact API paths
**Key finding:** `redirect_slashes=False` on backend — paths must match exactly

---

## Phase 1: Public Pages (no auth)

### 1.1 Homepage `/`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load — trending agents | `GET /api/v1/agents/?page=1&per_page=50&status=active` | Yes |
| Page load — social proof stats | `GET /api/v1/analytics/public-stats` | No |
| MagicBox search | `POST /api/v1/tasks/suggest` (auth) or keyword fallback `GET /api/v1/agents/` | — |

### 1.2 Agents Marketplace `/agents`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load — list agents | `GET /api/v1/agents/?page=1&per_page=12&status=active` | Yes |
| Search input | `POST /api/v1/discover/` | Yes |
| Category filter | `GET /api/v1/agents/?category=<slug>&status=active` | Yes |
| Pagination | `GET /api/v1/agents/?page=N&per_page=12&status=active` | Yes |

### 1.3 Agent Detail `/agents/[id]`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load — agent data | `GET /api/v1/agents/<id>` | No |
| Page load — agent card | `GET /api/v1/agents/<id>/card` | No |
| Page load — recommendations | `GET /api/v1/discover/recommend/<id>` | No |
| Try It (guest) | `POST /api/v1/tasks/guest-try` | No |
| Try It (auth) | `POST /api/v1/tasks/` | Yes |

### 1.4 Login `/login`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Google sign-in | Firebase popup → `POST /api/v1/auth/session` + `POST /api/v1/auth/firebase` | No |
| GitHub sign-in | Firebase popup → same as above | No |
| Email login (dev) | `POST /api/v1/auth/login` | No |

### 1.5 Register `/register`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Registration (dev) | `POST /api/v1/auth/register` | No |

### 1.6 Other Public Pages
| Page | API Calls | Notes |
|------|-----------|-------|
| `/pricing` | None | Static |
| `/docs` | None | Static |
| `/explore` | None | Static |
| `/guide` | None | Static |
| `/privacy` | None | Static |
| `/terms` | None | Static |
| `/register-agent` | `POST /api/v1/agents/detect` on detect, `POST /api/v1/agents/` on register | No / Yes |
| `/community-agents` | `GET /api/v1/custom-agents/` | Yes |
| `/community-agents/[id]` | `GET /api/v1/custom-agents/<id>` | No |

---

## Phase 2: Dashboard Pages (auth required)

### 2.1 Dashboard Overview `/dashboard`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load — balance | `GET /api/v1/credits/balance` | No |
| Page load — tasks | `GET /api/v1/tasks/` | Yes |
| Page load — agents | `GET /api/v1/agents/?owner_id=<uid>` | Yes |
| SSE stream | `GET /api/v1/activity/stream` | No |

### 2.2 My Agents `/dashboard/agents`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/agents/?owner_id=<uid>` | Yes |
| Delete agent | `DELETE /api/v1/agents/<id>` | No |

### 2.3 Agent Settings `/dashboard/agents/[id]`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/agents/<id>` + `/stats` + webhook-logs | No / Yes (logs) |
| Update agent | `PUT /api/v1/agents/<id>` | No |
| Delete permanently | `DELETE /api/v1/agents/<id>/permanent` | No |
| Webhook logs | `GET /api/v1/agents/<id>/webhook-logs/` | Yes |

### 2.4 Tasks List `/dashboard/tasks`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/tasks/?page=1&per_page=20` | Yes |
| Status filter | `GET /api/v1/tasks/?status=<val>&page=1` | Yes |

### 2.5 Task Detail `/dashboard/tasks/[id]`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load (polls 5s) | `GET /api/v1/tasks/<id>` | No |
| Cancel | `POST /api/v1/tasks/<id>/cancel` | No |
| Confirm | `POST /api/v1/tasks/<id>/confirm` | No |
| Rate | `POST /api/v1/tasks/<id>/rate` | No |
| Send message | `POST /api/v1/tasks/<id>/messages` | No |

### 2.6 New Task `/dashboard/tasks/new`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load — agent list | `GET /api/v1/agents/?per_page=20&status=active` | Yes |
| Search agents | `GET /api/v1/agents/?q=<query>&per_page=10` | Yes |
| Submit task | `POST /api/v1/tasks/` | Yes |

### 2.7 Credits `/dashboard/credits`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /credits/balance` + `/transactions` + `/usage` + `/spend-by-agent` | No (all) |
| Buy credits | `POST /api/v1/billing/credits-checkout` | No |

### 2.8 Payouts `/dashboard/payouts`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /payouts/connect/status` + `/balance` + `/history` | No (all) |
| Connect Stripe | `POST /api/v1/payouts/connect/onboard` | No |
| Request payout | `POST /api/v1/payouts/request` | No |

### 2.9 Workflows `/dashboard/workflows`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/workflows/` | Yes |
| Delete | `DELETE /api/v1/workflows/<id>` | No |
| Clone | `POST /api/v1/workflows/<id>/clone` | No |

### 2.10 Workflow Detail `/dashboard/workflows/[id]`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/workflows/<id>` + `/runs` (polls 3s) | No |
| Run | `POST /api/v1/workflows/<id>/run` | No |
| Cancel run | `POST /api/v1/workflows/runs/<runId>/cancel` | No |
| View output | `GET /api/v1/workflows/runs/<runId>/output` | No |
| Update | `PUT /api/v1/workflows/<id>` | No |

### 2.11 New Workflow `/dashboard/workflows/new`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Create manual/hierarchical | `POST /api/v1/workflows/` | Yes |
| Supervisor plan | `POST /api/v1/workflows/supervisor/plan` | No |
| Supervisor replan | `POST /api/v1/workflows/supervisor/replan` | No |
| Supervisor approve | `POST /api/v1/workflows/supervisor/approve` | No |

### 2.12 Schedules `/dashboard/schedules`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/schedules/` | Yes |
| Create | `POST /api/v1/schedules/` | Yes |
| Pause/Resume | `POST /api/v1/schedules/<id>/pause` or `/resume` | No |
| Delete | `DELETE /api/v1/schedules/<id>` | No |

### 2.13 Builder `/dashboard/builder`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | None (iframe to builder.crewhubai.com) | — |
| Publish submit | `POST /api/v1/builder/submissions` | No |

### 2.14 Builder Submissions `/dashboard/builder/submissions`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/builder/submissions?page=1&per_page=20` | No |
| Delete | `DELETE /api/v1/builder/submissions/<id>` | No |
| Resubmit | `POST /api/v1/builder/submissions/<id>/resubmit` | No |

### 2.15 Settings `/dashboard/settings`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load — LLM keys | `GET /api/v1/llm-keys/` | Yes |
| Page load — channels | `GET /api/v1/channels/` | Yes |
| Save spending limit | `PUT /api/v1/auth/me` | No |
| Generate API key | `POST /api/v1/auth/api-keys` | No |
| Revoke API key | `POST /api/v1/auth/revoke-api-key` | No |
| Set LLM key | `PUT /api/v1/llm-keys/<provider>` | No |
| Delete LLM key | `DELETE /api/v1/llm-keys/<provider>` | No |
| Download data | `GET /api/v1/auth/me/export` | No |
| Delete account | `DELETE /api/v1/auth/me` | No |
| Create channel | `POST /api/v1/channels/` | Yes |
| Update channel | `PATCH /api/v1/channels/<id>` | No |
| Delete channel | `DELETE /api/v1/channels/<id>` | No |

---

## Phase 3: Admin Pages (admin auth required)

### 3.1 Admin Overview `/admin`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/admin/stats` + `GET /health` | No |

### 3.2 Admin Users `/admin/users`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/admin/users/` | ⚠️ Yes |
| Update user status | `PUT /api/v1/admin/users/<id>/status` | No |

### 3.3 Admin Tasks `/admin/tasks`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load (polls 5s) | `GET /api/v1/admin/tasks/` | ⚠️ Yes |

### 3.4 Admin Transactions `/admin/transactions`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/admin/transactions/` | ⚠️ Yes |

### 3.5 Admin LLM Calls `/admin/calls`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/admin/llm-calls/` | ⚠️ Yes |

### 3.6 Admin Submissions `/admin/submissions`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/admin/submissions?status=pending_review` | No (fixed) |
| Approve | `POST /api/v1/admin/submissions/<id>/approve` | No |
| Reject | `POST /api/v1/admin/submissions/<id>/reject?notes=<encoded>` | No |
| Revoke | `POST /api/v1/admin/submissions/<id>/revoke` | No |

### 3.7 Admin Agents `/admin/agents`
| Action | API Call | Trailing Slash |
|--------|---------|----------------|
| Page load | `GET /api/v1/agents/?per_page=100` | Yes |
| Change status | `PUT /api/v1/admin/agents/<id>/status` | No |

---

## ⚠️ Trailing Slash Risk Summary

Backend has `redirect_slashes=False`. These frontend paths use trailing slashes
and WILL 404 if the backend decorator doesn't match:

**HIGH RISK — admin list endpoints with trailing slash in frontend:**
- `GET /api/v1/admin/users/` — frontend sends trailing slash
- `GET /api/v1/admin/tasks/` — frontend sends trailing slash
- `GET /api/v1/admin/transactions/` — frontend sends trailing slash
- `GET /api/v1/admin/llm-calls/` — frontend sends trailing slash

**Verified working (backend has trailing slash in decorator):**
- `GET/POST /api/v1/agents/` — matches
- `GET/POST /api/v1/tasks/` — matches
- `GET/POST /api/v1/workflows/` — matches
- `GET/POST /api/v1/schedules/` — matches
- `GET/POST /api/v1/channels/` — matches
- `GET /api/v1/llm-keys/` — matches

**Fixed in this session:**
- `GET /api/v1/admin/submissions` — removed trailing slash (was causing 404)

---

## Test Execution Order

1. **Phase 1** — Public pages (no login needed)
2. **Phase 2** — Dashboard (login once, test all pages)
3. **Phase 3** — Admin (login as admin, test all pages)

For each page: load it, verify no 404/500 errors in network tab, verify data renders, test each user action.
