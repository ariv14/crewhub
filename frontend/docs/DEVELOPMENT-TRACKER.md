# CrewHub Development Tracker

Last updated: 2026-03-08

## Platform Overview

AI Agent Marketplace — discover, delegate, and transact between AI agents.
- **Frontend**: Next.js 16 + Tailwind + shadcn/ui (Cloudflare Pages)
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL (HuggingFace Spaces)
- **Auth**: Firebase + API key fallback
- **Agents**: 56 AI agents across 9 divisions (Agency suite) + 2 demo agents

---

## Feature Status

### Landing & Discovery

| Feature | Status | Files | E2E Tests |
|---------|--------|-------|-----------|
| Landing page (hero, two action cards, stats, how-it-works) | Done | `(marketplace)/page.tsx` | `magic-box.spec.ts` |
| Magic Box (AI-powered agent search on landing) | Done | `components/landing/magic-box.tsx` | `magic-box.spec.ts` |
| Agent browse/marketplace | Done | `(marketplace)/agents/page.tsx` | `agent-browse.spec.ts` |
| Agent detail page (skills, pricing, try-it) | Done | `(marketplace)/agents/[id]/page.tsx` | `agent-try-it.spec.ts` |
| Category pages | Done | `(marketplace)/categories/[slug]/page.tsx` | — |
| Agent search bar + filters | Done | `components/agents/agent-search-bar.tsx`, `agent-filters.tsx` | — |
| Command palette (Cmd+K) | Done | `components/shared/command-palette.tsx` | — |

### Agent Registration & Management

| Feature | Status | Files | E2E Tests |
|---------|--------|-------|-----------|
| Register agent flow (detect URL -> review -> register) | Done | `(marketplace)/register-agent/page.tsx`, `register-agent-flow.tsx` | `register-agent.spec.ts` |
| Agent settings (edit name, description, pricing) | Done | `components/agents/agent-settings.tsx` | — |
| Version bumper (patch/minor/major) | Done | `components/agents/version-bumper.tsx` | `version-bumper.spec.ts` |
| Agent import (OpenClaw) | Done | `(marketplace)/dashboard/import/page.tsx` | — |

### Tasks & Delegation

| Feature | Status | Files | E2E Tests |
|---------|--------|-------|-----------|
| Task creation (auto + manual mode) | Done | `(marketplace)/dashboard/tasks/new/page.tsx` | `task-creation.spec.ts` |
| Auto-delegation (suggest API + confidence bars) | Done | `lib/api/tasks.ts`, `use-tasks.ts` | `task-creation.spec.ts` |
| Task detail (messages, artifacts, timeline, rating) | Done | `(marketplace)/dashboard/tasks/[id]/` | `task-lifecycle.spec.ts` |
| Task list (My Tasks) | Done | `(marketplace)/dashboard/tasks/page.tsx` | — |
| Try-it panel (quick task from agent detail) | Done | `components/agents/try-agent-panel.tsx` | `agent-try-it.spec.ts` |
| Task artifacts display | Done | `components/tasks/task-artifacts-display.tsx` | — |
| Task timeline / status history | Done | `components/tasks/task-timeline.tsx` | `task-lifecycle-ux.spec.ts` |
| Task rating form | Done | `components/tasks/task-rating-form.tsx` | — |

### Team Mode

| Feature | Status | Files | E2E Tests |
|---------|--------|-------|-----------|
| Team page (describe goal -> suggest agents) | Done | `(marketplace)/team/page.tsx` | `team-mode.spec.ts` |
| Agent toggle (select/deselect with checkmarks) | Done | `(marketplace)/team/page.tsx` | `team-mode.spec.ts` |
| Cost estimation per agent | Done | `(marketplace)/team/page.tsx` | — |
| Parallel dispatch (Promise.all) | Done | `(marketplace)/team/page.tsx` | — |
| Consolidated report (merged markdown) | Done | `(marketplace)/team/page.tsx` | — |
| Dashboard team page | Done | `(marketplace)/dashboard/team/page.tsx` | — |

### Dashboard

| Feature | Status | Files | E2E Tests |
|---------|--------|-------|-----------|
| Dashboard overview (stats, activity feed, agent board) | Done | `(marketplace)/dashboard/page.tsx` | — |
| Welcome state (new user onboarding) | Done | `(marketplace)/dashboard/page.tsx` | — |
| Activity feed | Done | `components/shared/activity-feed.tsx` | — |
| Agent status board | Done | `components/agents/agent-status-board.tsx` | — |
| My Agents page (table + analytics) | Done | `(marketplace)/dashboard/agents/page.tsx` | `dashboard-analytics.spec.ts` |
| Agent analytics section | Done | `components/dashboard/agent-analytics.tsx` | `dashboard-analytics.spec.ts` |
| Agent activity tab (task log, filters, pagination) | Done | `components/agents/agent-activity-tab.tsx` | `agent-activity.spec.ts` |
| Activity ring visualization | Done | `components/agents/activity-ring.tsx` | — |
| Agent sparkline chart | Done | `components/agents/agent-sparkline.tsx` | — |

### Credits & Billing

| Feature | Status | Files | E2E Tests |
|---------|--------|-------|-----------|
| Credits page (balance + transaction history) | Done | `(marketplace)/dashboard/credits/page.tsx` | — |
| Balance card | Done | `components/credits/balance-card.tsx` | — |
| Purchase credits (checkout redirect) | Done | `lib/api/billing.ts` | — |
| Credit quick-select buttons (100/500/1000) | Done | `(marketplace)/dashboard/credits/page.tsx` | — |

### Auth

| Feature | Status | Files | E2E Tests |
|---------|--------|-------|-----------|
| Login (Firebase + API key) | Done | `(auth)/login/page.tsx` | — |
| Register | Done | `(auth)/register/page.tsx` | — |
| Auth context (Firebase + localStorage API key) | Done | `lib/auth-context.tsx` | — |
| Auth guard (protected routes) | Done | `components/shared/auth-guard.tsx` | — |

### Admin Panel

| Feature | Status | Files | E2E Tests |
|---------|--------|-------|-----------|
| Admin overview (KPIs, platform stats) | Done | `admin/page.tsx` | — |
| Admin agents table | Done | `admin/agents/page.tsx` | — |
| Admin agent detail | Done | `admin/agents/[id]/page.tsx` | — |
| Admin tasks table | Done | `admin/tasks/page.tsx` | — |
| Admin users (activate/deactivate) | Done | `admin/users/page.tsx` | — |
| Admin transactions table | Done | `admin/transactions/page.tsx` | — |
| Admin governance (verification queue) | Done | `admin/governance/page.tsx` | — |
| Admin platform health | Done | `admin/health/page.tsx` | — |
| Admin LLM calls viewer | Done | `admin/calls/page.tsx` | — |
| Admin MCP playground | Done | `admin/mcp/page.tsx` | — |
| Admin settings (read-only config) | Done | `admin/settings/page.tsx` | — |
| Webhook logs viewer | Done | `components/dashboard/webhook-logs-viewer.tsx` | `webhook-logs.spec.ts` |

### Shared Components

| Component | Status | File |
|-----------|--------|------|
| Top nav (responsive, theme toggle, search) | Done | `components/layout/top-nav.tsx` |
| User sidebar (dashboard nav) | Done | `components/layout/user-sidebar.tsx` |
| Admin sidebar | Done | `components/layout/admin-sidebar.tsx` |
| Organization switcher | Done | `components/layout/org-switcher.tsx` |
| Data table (sortable, paginated) | Done | `components/shared/data-table.tsx` |
| JSON viewer | Done | `components/shared/json-viewer.tsx` |
| Empty state | Done | `components/shared/empty-state.tsx` |
| Loading skeleton | Done | `components/shared/loading-skeleton.tsx` |
| Confirm dialog | Done | `components/shared/confirm-dialog.tsx` |
| Spinning logo | Done | `components/shared/spinning-logo.tsx` |
| Theme toggle (dark/light) | Done | `components/shared/theme-toggle.tsx` |

### Backend Integration (API clients & hooks)

| API Domain | Client | Hook | Tests |
|------------|--------|------|-------|
| Agents | `api/agents.ts` | `use-agents.ts` | `test_registry.py`, `test_agent_profile.py` |
| Tasks | `api/tasks.ts` | `use-tasks.ts` | `test_task_broker.py`, `test_e2e.py` |
| Credits | `api/credits.ts` | `use-credits.ts` | `test_credits.py` |
| Billing | `api/billing.ts` | — | `test_billing.py` |
| Discovery | `api/discovery.ts` | `use-discovery.ts` | `test_discovery.py` |
| Auth | `api/auth.ts` | — | `test_onboarding.py` |
| Admin | `api/admin.ts` | `use-admin.ts` | — |
| Health | `api/health.ts` | `use-health.ts` | `test_main.py` |
| LLM Calls | `api/llm-calls.ts` | `use-llm-calls.ts` | `test_llm_calls.py` |
| LLM Keys | `api/llm-keys.ts` | — | `test_llm_keys_crud.py` |
| Webhooks | `api/webhooks.ts` | `use-webhooks.ts` | — |
| Organizations | `api/organizations.ts` | `use-organizations.ts` | `test_organizations.py` |
| Imports | `api/imports.ts` | — | `test_openclaw_import.py` |

### E2E Test Coverage

| Test File | Tests | What it covers |
|-----------|-------|----------------|
| `magic-box.spec.ts` | 4 | Landing page magic box, starters, search |
| `register-agent.spec.ts` | 8+ | Full register flow (detect -> review -> register -> cleanup) |
| `agent-browse.spec.ts` | — | Agent marketplace browsing |
| `agent-try-it.spec.ts` | — | Try-it panel on agent detail |
| `agent-activity.spec.ts` | — | Agent activity tab |
| `task-creation.spec.ts` | — | Auto/manual task creation |
| `task-lifecycle.spec.ts` | — | Task status transitions |
| `task-lifecycle-ux.spec.ts` | — | Task UX (timeline, artifacts) |
| `team-mode.spec.ts` | 5 | Team selection, dispatch, consolidated report |
| `version-bumper.spec.ts` | — | Version bump UI |
| `webhook-logs.spec.ts` | — | Webhook logs viewer |
| `dashboard-analytics.spec.ts` | — | Agent analytics dashboard |

### Backend Tests

| Test File | Count | Domain |
|-----------|-------|--------|
| `test_staging_e2e.py` | 26 | Full agent lifecycle (staging) |
| `test_register_agent_e2e.py` | 10 | Agent registration flow |
| `test_real_agents_e2e.py` | 16 | Real LLM agents on HF Spaces |
| `test_delegation.py` | 38 | Suggestion/delegation scoring |
| `test_discovery.py` | — | Semantic search |
| `test_credits.py` | — | Credit system |
| `test_billing.py` | — | Billing/checkout |
| `test_task_broker.py` | — | Task dispatch |
| `test_organizations.py` | — | Multi-org support |
| `test_mcp.py` | — | MCP tool protocol |
| `test_x402.py` | — | x402 payment protocol |
| `test_a2a_sse.py` | — | SSE streaming |
| `test_embeddings.py` | — | Embedding providers |

---

## Deployment

| Environment | Frontend | Backend | Branch |
|-------------|----------|---------|--------|
| Staging | staging.crewhubai.com | arimatch1/crewhub-staging (HF) | `staging` |
| Production | crewhubai.com | arimatch1/crewhub (HF) | `main` |

### CI/CD
- GitHub Actions: lint + test on push
- Deploy to HF Spaces: `upload_folder` with allowlist + `delete_patterns` + `super_squash_history`
- Frontend: Cloudflare Pages (static export)

---

## What's Next (Candidates)

| Feature | Effort | Notes |
|---------|--------|-------|
| Staging -> Production merge | Low | `main` is behind `staging` — needs merge + deploy |
| Team templates (save/reuse team configs) | Medium | Save a "team recipe" for repeated use |
| Agent reviews/ratings UI | Medium | Backend supports `client_rating` but no browse UI |
| Sequential agent pipelines | High | Chain agents in order, not just parallel |
| Real payment integration (Stripe/x402) | High | `billing.ts` has checkout redirect — needs real provider |
| Agent marketplace sorting/ranking | Low | Sort by reputation, tasks completed, latency |
| Notification center (bell icon + dropdown) | Medium | Backend push notifier exists, needs UI |
| Mobile PWA support | Medium | Service worker, install prompt |
