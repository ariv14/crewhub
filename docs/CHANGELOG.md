# Changelog

All notable changes to CrewHub are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[v0.1.0]: https://github.com/aidigitalcrew/crewhub/releases/tag/v0.1.0
