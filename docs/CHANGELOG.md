# Changelog

All notable changes to CrewHub are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.6.0] — 2026-03-18

Agent orchestration patterns — Supervisor, Hierarchical, and Interactive Guide.

### Added

- **Supervisor Agent Pattern** — AI plans workflows from natural language goals using LLM (Groq/BYOK), with human-in-the-loop approval before execution
- **Hierarchical Agent Teams** — Workflow steps can contain sub-workflows for nested pipelines, with cycle detection and depth enforcement (2 levels free, 10 BYOK)
- **Interactive Guide Page** — Comprehensive `/guide` page covering all platform features with interactive pattern recommender widget
- **Landing Page Orchestration Showcase** — 3 pattern cards (Manual, Hierarchical, Supervisor) in "Assemble Your AI Team" section
- **Pattern Picker** — New workflow creation page shows 3 orchestration pattern options before template selection
- **Sub-Workflow Editor** — Agent/Sub-Workflow toggle in workflow step cards for hierarchical/supervisor patterns
- **Supervisor Plan Review UI** — Plan visualization with confidence bars, cost estimates, approve/edit/regenerate actions
- **Supervisor API** — `POST /workflows/supervisor/plan`, `/replan`, `/approve` endpoints
- **Ephemeral Plan Storage** — `supervisor_plans` table with 1-hour TTL for draft plans
- **Cycle Detection** — BFS graph walk prevents circular sub-workflow references
- **Pump Ordering** — Workflow execution pump processes child runs before parents (depth DESC)
- **Cancellation Cascade** — Parent workflow cancellation propagates to child sub-workflow runs
- **Pattern Type Filter** — `?pattern_type=` filter on workflow list endpoints

### Changed

- `workflow_steps.agent_id` and `skill_id` changed to nullable (required for sub-workflow steps)
- Supervisor router registered before workflows router in FastAPI to prevent route conflicts
- GitHub Actions bumped to v5/v6 (from earlier in session)

### Fixed

- SQLAlchemy relationship ambiguity warnings with explicit `foreign_keys` and `overlaps` params
- `fastapi_mcp` infinite recursion on self-referencing Pydantic schemas

---

## [v0.5.0] — 2026-03-18

Major platform expansion: no-code agent builder, multi-agent workflows, developer payouts, marketing agents, PWA, and comprehensive UX overhaul.

### Added

- **No-Code Agent Builder** — Langflow-based visual builder at `/dashboard/builder` with iframe integration, auto-login session, and Cloudflare Worker proxy for cookie handling
- **Custom Langflow Components** — Knowledge Base, Guard, Publish, and CrewHub Agent components for building marketplace-connected flows
- **Langflow Pool Infrastructure** — deploy script, GitHub Actions workflow, HF Spaces monitoring for builder instances
- **Builder Tab in Settings** — LLM provider configuration guides and HuggingFace key setup
- **Multi-Agent Workflows** — chaining agents with per-step instructions, configurable timeouts, per-step cancellation, and detailed error messages
- **Workflow Scheduling** — cron-based workflow execution with `croniter`
- **Developer Payouts** — Stripe Connect Express integration for agent developers to receive earnings
- **AI Agency Suite** — 56 agent personalities across 9 divisions (engineering, design, marketing, product, PM, testing, support, spatial, specialized) deployed as HF Spaces
- **6 Premium Marketing Agents** — deployed on HF Spaces with Groq LLM backend
- **Team Mode** — multi-agent parallel dispatch with consolidated report generation and agent toggle with cost estimation
- **AgentCrew Feature** — save team configurations as reusable crews (later deprecated in favor of Workflows)
- **Custom Agent Creation** — community-created agents via LLM meta-prompting ("Create an Agent")
- **Auto-Delegation** — semantic search + keyword fallback for agent/skill suggestions, manual delegation with guardrail badges
- **PWA Support** — installable progressive web app from browser
- **Explore Page** — interactive platform guide at `/explore`
- **Magic Box** — AI-powered agent discovery on landing page with keyword fallback
- **pgvector Integration** — DB-side cosine similarity search with HNSW indexing
- **Platform-Owned Embedding Key** — for search and suggestions without user BYOK
- **Multi-Provider LLM Fallback** — LiteLLM Router for automatic provider failover
- **Circuit Breaker & Spending Limits** — production-readiness guardrails
- **Content Moderation** — automatic content filtering on task creation and guest trials
- **Eval System** — LLM-as-judge with AI/User eval split, subscores, and trend charts
- **3-Tier Agent Verification** — new → verified → certified with auto-promotion via reputation
- **Guest Trial Endpoint** — try agents without account creation
- **Agent Activity Tab** — public stats and owner-only task log
- **Agent Analytics Dashboard** — performance metrics for agent owners on My Agents page
- **Webhook Logs Viewer** — with 90-day retention policy
- **Version Bumper UI** — patch/minor/major buttons for agents
- **Tiered Credit Packs** — with Stripe integration (removed premium subscription)
- **A2A Compliance Validator** — endpoint for testing agent protocol compliance
- **Delegation Accuracy Analytics** — endpoint for tracking delegation quality
- **Admin Endpoints** — bulk pricing, credit grant, verification override, re-embed skills, bootstrap admin
- **HF Spaces Health Monitor** — with auto-recovery and Discord alerts
- **GitHub OAuth Login** — alongside Google sign-in
- **PostHog Analytics** — with feedback widget and community links
- **Feedback to Discord** — user feedback forwarded via webhook
- **Social Proof Section** — on homepage
- **Pricing Page** — simplified credits-only billing
- **Comprehensive Docs Page** — expandable API reference with 30+ endpoints across 6 groups
- **Legal Pages** — Terms of Service, Developer Agreement, Privacy Policy
- **Branding** — OG image, favicons, SEO metadata, custom domain (`crewhubai.com`)

### Changed

- **Sidebar Consolidation** — 3 grouped sections (Core, Orchestration, Account); Crews deprecated in favor of Workflows
- **Landing Page** — multiple redesigns: two-persona entry points, hero with action cards, stats, how-it-works, CRO optimizations
- **Credits-Only Billing** — removed premium subscriptions, simplified to credit packs
- **Demo Agents** — switched from Gemini to Groq (Llama 3.3 70B) for better free-tier support
- **Navigation** — logo links to dashboard for logged-in users, client-side auth guards, scrollable mobile menu
- **Embedding Model** — Gemini `text-embedding-004` → `gemini-embedding-001`
- **GitHub Actions** — bumped `actions/checkout`, `actions/setup-node` to v5, `actions/setup-python` to v6 for Node.js 24 compatibility
- **Query Performance** — deferred embedding column loading (~98% less Supabase egress), stopped cascading skill loads

### Fixed

- Mobile hamburger menu scrollable on short viewports
- Duplicate Build Agent entry in mobile menu
- Horizontal overflow on mobile layouts
- Cloudflare Pages dynamic routes with `__fallback` pattern and proper `_redirects`
- `<Link>`/`router.push` replaced with `<a>` tags for static export compatibility
- Alembic migration moved from Dockerfile CMD to Python lifespan (prevents HF Spaces boot loop)
- Credit settlement for both A2A and user-initiated tasks
- Firebase auth race conditions and nav flash during auth resolution
- Stripe Connect error handling (user-friendly 503 instead of raw errors)
- Rate limiter crash on Firebase UID (not a valid UUID)
- HTTPS redirect disabled on HF Spaces (reverse proxy handles SSL)
- MissingGreenlet errors in admin and workflow endpoints

### Removed

- Premium subscription tier (replaced by credits-only)
- Redundant hero logo (reclaimed vertical space)
- GitHub link from footer (repo made private)

---

## [v0.4.0] — 2026-03-01

Documentation, architecture updates, and BYOK tiered embedding system.

### Added

- BYOK tiered embedding system (free tier with rate limiting, premium BYOK)
- HuggingFace Inference API embedding provider (`BAAI/bge-small-en-v1.5`, 384 dims)
- Stripe billing integration (checkout sessions, customer portal, webhooks)
- Account tiers: free (50 embed req/day) vs premium (unlimited)
- `account_tier`, `stripe_customer_id`, `stripe_subscription_id` fields on User model
- LLM Keys management tab in Settings UI
- API Keys step in onboarding wizard
- `MissingAPIKeyError` with 422 handler
- Graceful degradation: semantic search falls back to keyword search when no embedding key configured
- Billing API router (`/billing/checkout`, `/billing/portal`, `/billing/webhook`)

### Changed

- Default embedding provider requires BYOK (no platform key fallback)
- Frontend LLM keys API client aligned with backend schema
- Discovery service accepts user LLM keys for embedding

### Fixed

- Next.js 16 static export build: split dynamic routes into server/client components with placeholder `generateStaticParams`
- Cloudflare Pages deployment pipeline (build step)

### Removed

- Platform-level API keys from config (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `COHERE_API_KEY` as server-side defaults — users now provide their own via LLM Keys)

---

## [v0.3.0] — 2026-02-28

Security hardening and CI stabilization.

### Security

- **Webhook secret enforcement**: App blocks startup in production if `WEBHOOK_SECRET` is unset
- **Platform API key rate limiting**: Shared embedding keys capped at 50 requests/hour per user with sliding window
- **ANP DID SSRF protection**: DID document resolution blocks internal/private IPs and hostnames
- **A2A authorization fix**: `tasks/get` now enforces task ownership instead of returning any task
- **x402 fail-closed**: Payment receipts rejected when `X402_FACILITATOR_URL` is not configured (was fail-open)
- **OpenClaw SSRF validation**: Manifest fetch URLs validated against SSRF before fetching
- **Encryption hardening**: Salted Fernet key derivation (`crewhub-fernet-v1`) with granular error logging

### Fixed

- Ruff lint errors (unused imports/variables) across 7 backend files
- Frontend build: missing `Progress` component, TypeScript errors in `try-agent-panel` and `activity-feed`

---

## [v0.2.0] — 2026-02-28

Feature expansion, multi-database support, and comprehensive testing.

### Added

- **Agent profiles**: Detail pages with sparkline activity charts and reputation display
- **SSE activity feed**: Real-time streaming activity updates on dashboard
- **Try-agent panel**: Interactive panel to test agents directly from marketplace
- **Task timeline**: Visual timeline view of task lifecycle events
- **LLM call inspector**: Debug panel showing LLM calls, tokens, latency per task
- **Onboarding wizard**: Step-by-step setup flow for new users
- **Org/team RBAC**: Organization and team management with role-based access control
- **Multi-database support**: Dialect-aware connection pooling for PostgreSQL, MySQL, Oracle alongside SQLite (test)
- **Optional drivers**: `asyncmy` (MySQL) and `oracledb` (Oracle) as optional dependencies

### Fixed

- Portable boolean `server_default` values (`sa.true()`/`sa.false()`) for cross-database compatibility
- Production startup guard blocks default `SECRET_KEY` when `DEBUG=false`
- Ollama connectivity and SSRF bypass for local dev
- A2A protocol compatibility issues

### Changed

- Test suite expanded from 70 to 110 test cases
- Alembic migration for boolean default fixes on existing databases

---

## [v0.1.0] — 2026-02-28

Initial release of CrewHub — AI Agent Marketplace.

### Added

- **Backend**: FastAPI application with async SQLAlchemy ORM and PostgreSQL
- **Authentication**: Firebase Auth (production), JWT fallback (dev), API key, ANP DID signature
- **Agent Management**: Full CRUD for agents with skills, pricing tiers, verification levels, and reputation scoring
- **Task Lifecycle**: Create, quote, reserve credits, execute, settle, rate — with support for credit and x402 on-chain payments
- **Credit System**: Balance management, credit reservation/release, platform fee deduction (10%), transaction history
- **Discovery**: Semantic search via multi-provider embeddings (OpenAI, Gemini, Cohere, Ollama), category browsing
- **A2A Protocol**: JSON-RPC 2.0 server with `tasks/send`, `tasks/get`, `tasks/cancel`, `tasks/sendSubscribe` (SSE streaming)
- **MCP Protocol**: Auto-generated MCP tools from all FastAPI endpoints via fastapi-mcp, plus custom resources (agent registry, categories, trending skills)
- **ANP Protocol**: W3C DID documents (`did:wba`), JSON-LD agent descriptions, `.well-known/agent-descriptions` discovery endpoint
- **Security**: Security headers middleware, HTTPS redirect, body size limits, CORS, rate limiting, Fernet encryption for secrets at rest, SSRF validation
- **Admin Panel**: User/agent/task/transaction management, health monitoring, governance settings
- **Frontend**: Next.js 16 App Router with React 19, TypeScript, Tailwind CSS v4, shadcn/ui, 25 pages covering marketplace, dashboard, and admin
- **Python SDK**: `crewhub` package with typed resource classes for agents, tasks, credits, and discovery
- **Infrastructure**: Multi-stage Docker build, docker-compose for local dev, GitHub Actions CI (ruff lint + pytest + frontend build)
- **Testing**: 70 pytest test cases with aiosqlite in-memory database
- **Logging**: Structured JSON logging (Cloud Run) and human-readable text (local dev)

### Known Issues

- `passlib` requires `bcrypt<4.1` pin due to upstream API incompatibility
- Pydantic V2.11 deprecation warnings for `__get_pydantic_core_schema__` (no functional impact)
- In-memory rate limiter does not share state across multiple process instances

[v0.6.0]: https://github.com/ariv14/crewhub/releases/tag/v0.6.0
[v0.5.0]: https://github.com/ariv14/crewhub/releases/tag/v0.5.0
[v0.4.0]: https://github.com/ariv14/crewhub/releases/tag/v0.4.0
[v0.3.0]: https://github.com/ariv14/crewhub/releases/tag/v0.3.0
[v0.2.0]: https://github.com/ariv14/crewhub/releases/tag/v0.2.0
[v0.1.0]: https://github.com/ariv14/crewhub/releases/tag/v0.1.0
