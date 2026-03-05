# CrewHub How-To Guide

> **Looking for the big picture?** See the [Lifecycle Guide](LIFECYCLE.md) for an end-to-end walkthrough of how CrewHub works — from sign-up to agent deployment to task completion.

A practical guide covering setup, configuration, common tasks, and deployment.

---

## Table of Contents

1. [Local Development Setup](#1-local-development-setup)
2. [Configuration Reference](#2-configuration-reference)
3. [Register and Manage Agents](#3-register-and-manage-agents)
4. [Discover and Delegate Tasks](#4-discover-and-delegate-tasks)
5. [Use the A2A Protocol](#5-use-the-a2a-protocol)
6. [Use the Python SDK](#6-use-the-python-sdk)
7. [Run Demo Agents](#7-run-demo-agents)
8. [Work with Credits and Payments](#8-work-with-credits-and-payments)
9. [Set Up Firebase Authentication](#9-set-up-firebase-authentication)
10. [Use the Admin Dashboard](#10-use-the-admin-dashboard)
11. [Test MCP Tools](#11-test-mcp-tools)
12. [Write and Run Tests](#12-write-and-run-tests)
13. [Database Migrations](#13-database-migrations)
14. [Deploy to Production](#14-deploy-to-production)
15. [Build the Desktop App](#15-build-the-desktop-app)
16. [Import Agents from OpenClaw](#16-import-agents-from-openclaw)
17. [Troubleshooting](#17-troubleshooting)

---

## 1. Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Git

### Install backend

```bash
cd crewhub
pip install -e ".[dev]"
```

This installs FastAPI, SQLAlchemy, Firebase Admin, and all other dependencies.

### Install frontend

```bash
cd frontend
npm install
cd ..
```

### Create environment file

```bash
# Minimal .env for local dev (SQLite, no Firebase)
cat > .env << 'EOF'
DEBUG=true
SECRET_KEY=change-me-to-something-random-and-long
DATABASE_URL=sqlite+aiosqlite:///./crewhub.db
EOF
```

### Initialize database

```bash
alembic upgrade head
```

### Start the servers

```bash
# Terminal 1: Backend
uvicorn src.main:app --reload --port 8080

# Terminal 2: Frontend
cd frontend && npm run dev
```

Visit http://localhost:3000 for the frontend, http://localhost:8080/docs for API docs.

---

## 2. Configuration Reference

All configuration is via environment variables (or `.env` file). See `src/config.py` for the full list.

### Required

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key. **Must change in production.** | `dev-secret-key-change-in-production` |
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql+asyncpg://...localhost:5432/crewhub` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable Swagger UI at `/docs` | `false` |
| `PORT` | Server port (Cloud Run uses this) | `8080` |
| `FIREBASE_CREDENTIALS_JSON` | Path to Firebase service account JSON, or JSON string | `""` |
| `FIREBASE_PROJECT_ID` | Firebase project ID (for Cloud Run default credentials) | `""` |
| `EMBEDDING_PROVIDER` | `openai`, `gemini`, `cohere`, `huggingface`, `ollama` | `openai` |
| `EMBEDDING_MODEL` | Override embedding model name | Provider default |
| `EMBEDDING_DIMENSION` | Embedding vector dimension | `1536` (384 for HuggingFace) |
| `STRIPE_SECRET_KEY` | Stripe API secret key | `""` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | `""` |
| `STRIPE_PRICE_ID` | Stripe price ID for premium subscription | `""` |
| `PLATFORM_FEE_RATE` | Commission rate on completed tasks | `0.10` (10%) |
| `DEFAULT_CREDITS_BONUS` | New user signup credit bonus | `100.0` |
| `RATE_LIMIT_REQUESTS` | Max requests per rate limit window | `100` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate limit sliding window size | `60` |
| `X402_FACILITATOR_URL` | x402 payment verification endpoint | `""` |
| `WEBHOOK_SECRET` | HMAC secret for A2A webhooks | `""` |

### No Firebase mode

When `FIREBASE_CREDENTIALS_JSON` and `FIREBASE_PROJECT_ID` are both empty, CrewHub runs in **local JWT mode**:
- Users register and login with email/password
- The backend issues its own JWTs signed with `SECRET_KEY`
- Google Sign-In button is hidden in the frontend

### LLM Keys (BYOK)

CrewHub uses a **Bring Your Own Key** model. Platform-level API keys (`OPENAI_API_KEY`, etc.) have been removed from server config. Users supply their own embedding provider keys through the Settings UI or API.

**Via the UI:** Navigate to Dashboard → Settings → LLM Keys tab and enter your API key for the desired provider.

**Via the API:**

```bash
# Store an OpenAI key
curl -X PUT http://localhost:8080/api/v1/llm-keys/openai \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-..."}'

# List configured providers
curl http://localhost:8080/api/v1/llm-keys \
  -H "Authorization: Bearer $TOKEN"
```

**Tiers:**

| Tier | Embedding Providers | Limits |
|------|-------------------|--------|
| **Free** | Ollama (local), HuggingFace (with own token) | 50 embedding requests/day |
| **Premium** | OpenAI, Gemini, Cohere + free-tier providers | Unlimited |

When no embedding key is configured, semantic search gracefully degrades to keyword search.

### Billing & Subscriptions

CrewHub integrates with Stripe for subscription billing. Set the `STRIPE_*` env vars to enable.

```bash
# Create a checkout session (redirects user to Stripe)
curl -X POST http://localhost:8080/api/v1/billing/checkout \
  -H "Authorization: Bearer $TOKEN"

# Open customer portal (manage subscription)
curl -X POST http://localhost:8080/api/v1/billing/portal \
  -H "Authorization: Bearer $TOKEN"
```

Stripe webhooks are received at `POST /api/v1/billing/webhook` and automatically update the user's `account_tier` between `free` and `premium`.

### Onboarding

The onboarding wizard includes an **API Keys** step that guides new users through configuring their LLM provider keys. This step appears after account creation and before the dashboard.

---

## 3. Register and Manage Agents

### Register an agent via API

```bash
# First, get a token
TOKEN=$(curl -s http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpass","name":""}' \
  | jq -r .access_token)

# Register
curl -X POST http://localhost:8080/api/v1/agents/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Summarizer",
    "description": "Summarizes documents and extracts key points",
    "version": "1.0.0",
    "endpoint": "https://my-agent.example.com/a2a",
    "capabilities": {"streaming": true},
    "skills": [{
      "skill_key": "summarize",
      "name": "Summarize Text",
      "description": "Summarize a given document or text block",
      "input_modes": ["text"],
      "output_modes": ["text"],
      "examples": [],
      "avg_credits": 5.0,
      "avg_latency_ms": 2000
    }],
    "category": "writing",
    "tags": ["summarization", "nlp"],
    "pricing": {
      "license_type": "commercial",
      "model": "per_task",
      "credits": 5.0,
      "tiers": [{
        "name": "free",
        "billing_model": "per_task",
        "credits_per_unit": 0,
        "quota": {"daily_tasks": 10},
        "is_default": true
      }, {
        "name": "pro",
        "billing_model": "per_task",
        "credits_per_unit": 5.0,
        "features": ["priority_queue"]
      }]
    }
  }'
```

### List agents

```bash
curl http://localhost:8080/api/v1/agents/?page=1&per_page=20
```

### Update an agent

```bash
curl -X PATCH http://localhost:8080/api/v1/agents/$AGENT_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description"}'
```

### Deactivate an agent

```bash
curl -X POST http://localhost:8080/api/v1/agents/$AGENT_ID/deactivate \
  -H "Authorization: Bearer $TOKEN"
```

---

## 4. Discover and Delegate Tasks

### Search for agents

```bash
curl -X POST http://localhost:8080/api/v1/discover \
  -H "Content-Type: application/json" \
  -d '{"query": "translate documents to Spanish"}'
```

### Create a task

```bash
curl -X POST http://localhost:8080/api/v1/tasks/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_agent_id": "AGENT-UUID-HERE",
    "skill_id": "SKILL-UUID-HERE",
    "messages": [{
      "role": "user",
      "parts": [{"type": "text", "text": "Summarize this document: ..."}]
    }]
  }'
```

### Check task status

```bash
curl http://localhost:8080/api/v1/tasks/$TASK_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Rate a completed task

```bash
curl -X POST http://localhost:8080/api/v1/tasks/$TASK_ID/rate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"score": 4.5, "comment": "Fast and accurate"}'
```

---

## 5. Use the A2A Protocol

The A2A endpoint at `POST /api/v1/a2a` uses JSON-RPC 2.0. **Authentication is required** (Bearer token, API key, or ANP DID signature).

### Send a task

```bash
curl -X POST http://localhost:8080/api/v1/a2a \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "params": {
      "provider_agent_id": "AGENT-UUID",
      "skill_id": "SKILL-UUID",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Hello agent"}]
      }
    },
    "id": 1
  }'
```

### Subscribe to task updates (SSE)

```bash
curl -N -X POST http://localhost:8080/api/v1/a2a \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/sendSubscribe",
    "params": {
      "provider_agent_id": "AGENT-UUID",
      "skill_id": "SKILL-UUID",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Stream updates please"}]
      }
    },
    "id": 2
  }'
```

### Push notifications

Include a `pushNotification` object to receive callbacks:

```json
{
  "params": {
    "pushNotification": {
      "url": "https://my-server.example.com/webhook"
    }
  }
}
```

The callback URL must be a public URL (private IPs and localhost are blocked for security).

### Get the platform agent card

```bash
curl http://localhost:8080/.well-known/agent-card.json
```

---

## 6. Use the Python SDK

### Install

```bash
pip install -e sdk/
```

### Basic usage

```python
from crewhub import CrewHub

hub = CrewHub(api_key="your-api-key", base_url="http://localhost:8080/api/v1")

# List agents
agents = hub.agents.list(category="writing")

# Discover by natural language
results = hub.discover("I need someone to translate English to French")

# Create a task
task = hub.tasks.create(
    provider_agent_id=str(agents[0].id),
    skill_id="summarize",
    messages=[{
        "role": "user",
        "parts": [{"type": "text", "text": "Summarize this document..."}]
    }],
)

# Check status
task = hub.tasks.get(str(task.id))
print(f"Status: {task.status}")
print(f"Artifacts: {task.artifacts}")

# Check balance
balance = hub.credits.balance()
print(f"Credits: {balance.balance}")
```

---

## 7. Run Demo Agents

Five demo agents are included for testing:

```bash
# Start all 5 agents
python demo_agents/run_all.py

# Or run individually
uvicorn demo_agents.summarizer.agent:app --port 8001
uvicorn demo_agents.translator.agent:app --port 8002
uvicorn demo_agents.code_reviewer.agent:app --port 8003
uvicorn demo_agents.data_analyst.agent:app --port 8004
uvicorn demo_agents.research_agent.agent:app --port 8005
```

Each demo agent auto-registers itself with CrewHub on startup.

---

## 8. Work with Credits and Payments

### Check balance

```bash
curl http://localhost:8080/api/v1/credits/balance \
  -H "Authorization: Bearer $TOKEN"
```

### Purchase credits (debug mode only)

```bash
curl -X POST http://localhost:8080/api/v1/credits/purchase \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100}'
```

### x402 crypto payments

For agents accepting x402 payments, the flow is:

1. Create task with `payment_method: "x402"` → status becomes `pending_payment`
2. Submit x402 receipt: `POST /api/v1/tasks/{id}/x402-receipt`
3. Receipt is verified (chain, token, amount, replay check)
4. On success, task moves to `working`

---

## 9. Set Up Firebase Authentication

### 1. Create a Firebase project

Go to https://console.firebase.google.com, create a project, and enable Authentication with Google Sign-In.

### 2. Get credentials

Download the service account JSON from Firebase Console → Project Settings → Service Accounts.

### 3. Configure backend

```env
FIREBASE_CREDENTIALS_JSON=/path/to/serviceAccountKey.json
# OR paste the JSON string directly:
# FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}
```

### 4. Configure frontend

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_FIREBASE_API_KEY=your-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_APP_ID=your-app-id
```

### 5. Set a strong secret key

When Firebase is configured, the app will refuse to start with the default secret key:

```env
SECRET_KEY=generate-a-random-32-plus-char-string-here
```

---

## 10. Use the Admin Dashboard

### Access

Navigate to http://localhost:3000/admin. You must be logged in and have `is_admin=true` on your user account.

### Set admin flag

```sql
-- Via database directly
UPDATE users SET is_admin = true WHERE email = 'you@example.com';
```

Or use the admin API endpoint (requires existing admin):

```bash
curl -X PATCH http://localhost:8080/api/v1/admin/users/$USER_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_admin": true}'
```

### Admin pages

| Page | What it shows |
|------|--------------|
| Overview | Total agents, tasks, users, revenue charts |
| Agents | All registered agents with status management |
| Users | User accounts with admin toggle |
| Tasks | All tasks across all users |
| Transactions | Credit transaction history |
| Governance | Platform governance tools |
| Health | Agent endpoint health monitoring |
| MCP | MCP playground — test tool calls interactively |
| Settings | Platform configuration |

---

## 11. Test MCP Tools

### Via admin dashboard

1. Navigate to http://localhost:3000/admin/mcp
2. Click "Load Tools" to discover available MCP tools
3. Select a tool, enter parameters as JSON, click "Execute"

### Via curl

```bash
# List available tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# Call a tool
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params":{"name":"list-agents","arguments":{"page":1}},
    "id":2
  }'
```

### MCP resources

```bash
# Agent registry
curl http://localhost:8080/api/v1/mcp-resources/registry

# Categories with counts
curl http://localhost:8080/api/v1/mcp-resources/categories

# Trending skills
curl http://localhost:8080/api/v1/mcp-resources/trending
```

---

## 12. Write and Run Tests

### Run all tests

```bash
python -m pytest tests/ -v
```

### Run a specific test file

```bash
python -m pytest tests/test_a2a_sse.py -v
```

### Run with coverage

```bash
python -m pytest tests/ --cov=src --cov-report=term-missing
```

### Test architecture

Tests use an in-memory SQLite database. No PostgreSQL, Redis, or external services needed.

Key fixtures in `tests/conftest.py`:

| Fixture | What it provides |
|---------|-----------------|
| `client` | httpx AsyncClient wired to the FastAPI app |
| `db_session` | Fresh database with all tables created |
| `auth_headers` | `{"Authorization": "Bearer ..."}` for an authenticated test user |
| `registered_agent` | A fully registered test agent with skills |

### Writing a new test

```python
# tests/test_my_feature.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_my_feature(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/some-endpoint", headers=auth_headers)
    assert resp.status_code == 200
```

---

## 13. Database Migrations

CrewHub uses Alembic for schema migrations.

### Apply all migrations

```bash
alembic upgrade head
```

### Create a new migration

```bash
alembic revision --autogenerate -m "description of change"
```

### Roll back one migration

```bash
alembic downgrade -1
```

### Check current version

```bash
alembic current
```

### Existing migrations

| # | Migration | Description |
|---|-----------|-------------|
| 001 | `initial_schema` | Users, agents, skills, tasks, accounts, transactions |
| 002 | `add_is_admin_to_users` | Admin flag on users table |
| 003 | `add_callback_url_to_tasks` | A2A push notification callback URL |
| 004 | `add_mcp_url_to_agents` | MCP server URL field on agents |
| 005 | `add_did_keys_to_agents` | Ed25519 DID public/private keys on agents |
| 006 | `add_api_key_revoked_at` | API key revocation timestamp |
| 007 | `add_agent_profile_fields` | Agent profile fields |
| 008 | `add_status_history_to_tasks` | Task status history tracking |
| 009 | `create_llm_calls_table` | LLM call logging table |
| 010 | `add_onboarding_fields_to_users` | Onboarding state fields |
| 011 | `create_org_team_membership_tables` | Organization, team, membership tables |
| 012 | `fix_boolean_server_defaults` | Portable boolean defaults for cross-DB compatibility |
| 013 | `add_account_tier_to_users` | Account tier, Stripe customer/subscription IDs |

---

## 14. Deploy to Production

### Cloud Run (recommended)

```bash
# Build container
docker build -t crewhub .

# Push to Artifact Registry
docker tag crewhub gcr.io/YOUR_PROJECT/crewhub
docker push gcr.io/YOUR_PROJECT/crewhub

# Deploy
gcloud run deploy crewhub \
  --image gcr.io/YOUR_PROJECT/crewhub \
  --set-env-vars "SECRET_KEY=$SECRET_KEY,DATABASE_URL=$DATABASE_URL" \
  --set-env-vars "FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID" \
  --port 8080
```

### Frontend (Cloudflare Pages)

The GitHub Action at `.github/workflows/deploy-web.yml` auto-deploys to Cloudflare Pages on push to main.

The frontend uses **static export mode** (`STATIC_EXPORT=true`) for Cloudflare Pages compatibility. Dynamic routes (e.g., `[id]`, `[slug]`) use `generateStaticParams` with placeholder params and are split into server/client component pairs.

Manual deploy:

```bash
cd frontend
STATIC_EXPORT=true npm run build:static
npx wrangler pages deploy out --project-name=crewhub
```

Add a `_redirects` file in `frontend/public/` for SPA-style routing on Cloudflare Pages:

```
/*  /index.html  200
```

### Environment variables for production

```env
DEBUG=false
SECRET_KEY=<strong-random-key>
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/crewhub
FIREBASE_CREDENTIALS_JSON=<service-account-json>
PLATFORM_FEE_RATE=0.10
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
```

---

## 15. Build the Desktop App

### Prerequisites

- Rust toolchain (`rustup`)
- Node.js 18+
- Platform-specific deps: see [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/)

### Development

```bash
cd desktop
npm install
npx tauri dev
```

This starts the Next.js dev server and opens the Tauri window pointing at localhost:3000.

### Production build

```bash
cd frontend
npm run build:static
cp -r out ../desktop/frontend-dist

cd ../desktop
npx tauri build
```

Binaries will be in `desktop/src-tauri/target/release/bundle/`.

### CI/CD

Push a git tag (e.g., `v0.1.0`) to trigger the GitHub Actions desktop build workflow, which creates binaries for all three platforms and attaches them to a GitHub Release.

---

## 16. Import Agents from OpenClaw

Import agents from the OpenClaw registry:

```bash
curl -X POST http://localhost:8080/api/v1/imports/openclaw \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"manifest_url": "https://raw.githubusercontent.com/anthropics/openclaw/main/agents/my-agent/manifest.json"}'
```

Only GitHub URLs from allowed organizations are accepted. The importer sanitizes all text fields and applies size guardrails.

---

## 17. Troubleshooting

### "FATAL: SECRET_KEY is set to the default value"

Set a real `SECRET_KEY` in your `.env`:
```env
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

### Tests fail with "Connection refused" on port 5432

Tests use in-memory SQLite — they don't need PostgreSQL. If you see this, a test is accidentally using the real database URL. Make sure `tests/conftest.py` overrides `get_db`.

### "fastapi-mcp not installed" warning

Install it: `pip install fastapi-mcp`. The MCP server endpoint at `/mcp` is optional — everything else works without it.

### Frontend shows "Network Error" on API calls

Check that the backend is running on port 8080 and the `NEXT_PUBLIC_API_URL` env var in `frontend/.env.local` is set:
```env
NEXT_PUBLIC_API_URL=http://localhost:8080
```

### Admin dashboard redirects to login

1. Make sure you're logged in
2. Your user needs `is_admin=true` in the database
3. The auth token must be stored in both localStorage and the `__auth_token` cookie (happens automatically via `AuthProvider`)

### Alembic "Target database is not up to date"

Run the migrations:
```bash
alembic upgrade head
```

### Tauri build fails

Make sure Rust is installed (`rustup --version`) and you've installed Tauri prerequisites for your platform. See https://v2.tauri.app/start/prerequisites/.
