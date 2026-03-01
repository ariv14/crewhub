# Changelog

All notable changes to CrewHub are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[v0.4.0]: https://github.com/ariv14/crewhub/releases/tag/v0.4.0
[v0.3.0]: https://github.com/ariv14/crewhub/releases/tag/v0.3.0
[v0.2.0]: https://github.com/ariv14/crewhub/releases/tag/v0.2.0
[v0.1.0]: https://github.com/ariv14/crewhub/releases/tag/v0.1.0
