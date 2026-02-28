# CrewHub Real-Work Demo — Design Document

## Goal

A working demo where AI agents discover each other on the marketplace, delegate tasks via A2A protocol, call real LLMs (local via Ollama or paid APIs), and show the full orchestration with live activity tracking — all at zero cost using local models.

## Demo Story

A user opens CrewHub, browses the marketplace (5 agents registered), and submits a research task: "Summarize the latest AI agent frameworks and translate the summary to Spanish."

The Research Agent:
1. Discovers a Summarizer and Translator on the marketplace via CrewHub's discovery API
2. Delegates summarization → Summarizer Agent calls an LLM via LiteLLM
3. Delegates translation → Translator Agent calls an LLM via LiteLLM
4. Composes results and returns them to the user
5. Credits are deducted at each step, visible in the dashboard
6. Admin panel shows a live activity feed of the entire orchestration

## Architecture

```
User Browser → Frontend (Next.js :3000)
                  ↓
              Backend API (FastAPI :8080)
              ├── Agent Registry + Discovery
              ├── Task Broker + Credit Ledger
              ├── Activity Feed (SSE)
              └── A2A Protocol
                  ↓ delegates via A2A
    ┌─────────────┼─────────────┬─────────────┐
    ↓             ↓             ↓             ↓
Summarizer    Translator    Code Reviewer   Data Analyst
  (:8001)      (:8002)       (:8003)        (:8004)
    │             │             │              │
    └──────────── LiteLLM ─────┴──────────────┘
                    ↓
              Ollama (local, free)
              or OpenAI / Anthropic / any provider
```

## Zero-Cost Stack

| Component | Provider | Cost |
|-----------|----------|------|
| Database | SQLite | Free |
| LLM | Ollama (llama3.2, mistral) | Free |
| LLM abstraction | LiteLLM | Free |
| Backend | FastAPI (local) | Free |
| Frontend | Next.js (local) | Free |
| Hosting (later) | VPS / Railway / Fly.io | ~$5-20/mo |

## Phases

### Phase 1: LLM-Powered Demo Agents

**Goal**: Replace heuristic demo agents with real LLM-powered ones via LiteLLM + Ollama.

#### 1.1 Add LiteLLM dependency

- Add `litellm` to `pyproject.toml` dependencies
- Each agent reads `MODEL` env var (default: `ollama/llama3.2`)

#### 1.2 Upgrade demo agents

Each agent's core logic changes from heuristics to a LiteLLM call. The A2A protocol layer stays identical.

**Summarizer** (`demo_agents/summarizer/agent.py`):
- System prompt: "You are a text summarizer. Provide concise summaries."
- Input: user text → Output: summary

**Translator** (`demo_agents/translator/agent.py`):
- System prompt: "You are a translator. Translate text to the requested language."
- Input: text + target language → Output: translated text

**Code Reviewer** (`demo_agents/code_reviewer/agent.py`):
- System prompt: "You are a code reviewer. Review the code for bugs, style, and improvements."
- Input: code → Output: review comments

**Data Analyst** (`demo_agents/data_analyst/agent.py`):
- System prompt: "You are a data analyst. Analyze the provided data and give insights."
- Input: CSV/data → Output: analysis

**Research Agent** (`demo_agents/research/agent.py`):
- This is the orchestrator. It:
  1. Calls CrewHub discovery API to find agents by capability
  2. Delegates sub-tasks via A2A `tasks/send`
  3. Polls/streams results via A2A `tasks/get`
  4. Composes final response using its own LLM call

#### 1.3 Agent config via environment

Each agent reads:
```env
MODEL=ollama/llama3.2          # or claude-sonnet-4-20250514, gpt-4o-mini, etc.
OPENAI_API_KEY=                # only if using OpenAI models
ANTHROPIC_API_KEY=             # only if using Anthropic models
CREWHUB_API_URL=http://localhost:8080  # marketplace URL (for research agent)
```

### Phase 2: Seed Script + One-Command Demo

**Goal**: Single script that starts everything, seeds data, opens browser.

#### 2.1 Seed script (`scripts/seed.py`)

- Creates a demo user (email: demo@crewhub.local, password: DemoPass123)
- Creates an admin user (email: admin@crewhub.local, password: AdminPass123)
- Promotes admin user to `is_admin=True`
- Registers all 5 demo agents in the marketplace with proper skills, pricing, descriptions
- Credits 1000 credits to demo user

#### 2.2 Demo launcher (`scripts/demo.sh`)

```bash
#!/bin/bash
# 1. Check Ollama is running (prompt to install if not)
# 2. Pull required model (ollama pull llama3.2)
# 3. Install Python + Node dependencies
# 4. Start backend (SQLite mode)
# 5. Run seed script
# 6. Start 5 demo agents
# 7. Start frontend
# 8. Open browser to http://localhost:3000
# 9. Print "Demo ready!" with credentials
```

All processes managed with proper cleanup on Ctrl+C.

### Phase 3: Live Activity Dashboard

**Goal**: Real-time visibility into multi-agent orchestration in the admin panel.

#### 3.1 Activity event model

Add a lightweight `activity_events` table (or in-memory buffer for demo):
```
id | timestamp | event_type | agent_id | task_id | detail | metadata
```

Event types:
- `agent.discovered` — Agent A found Agent B via discovery
- `task.delegated` — Task sent from one agent to another
- `llm.called` — LLM invocation (model, tokens, latency)
- `task.completed` — Task finished with result
- `credits.charged` — Credits deducted

#### 3.2 Backend SSE endpoint

`GET /api/v1/admin/activity/stream` — SSE endpoint that streams activity events in real-time.

#### 3.3 Frontend activity feed

Add a "Live Activity" tab or panel in the admin dashboard:
- Real-time feed of events with timestamps
- Color-coded by event type
- Shows the agent-to-agent flow visually
- Auto-scrolls as new events arrive

### Phase 4: Docker Compose + Hosted Deployment

**Goal**: Containerize everything for cloud deployment.

#### 4.1 Docker Compose (`docker-compose.demo.yml`)

Services:
- `postgres` — PostgreSQL 16
- `backend` — FastAPI app
- `summarizer`, `translator`, `code_reviewer`, `data_analyst`, `research` — 5 agent containers
- `frontend` — Next.js (or static export behind nginx)
- `ollama` — Ollama server with pre-pulled models (or use cloud LLM APIs)
- `caddy` — Reverse proxy with auto-HTTPS

#### 4.2 Deploy to cloud

Options (in order of simplicity):
1. **Railway** — `railway up` with docker-compose, auto-HTTPS, ~$5/mo
2. **Fly.io** — Fly Machines for each service, geo-distributed
3. **Single VPS** — DigitalOcean/Hetzner droplet with Docker Compose

#### 4.3 Hosted URL

`demo.aidigitalcrew.com` — pointing to the deployed instance.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `pyproject.toml` | Modify | Add `litellm` dependency |
| `demo_agents/base.py` | Modify | Add LiteLLM helper, activity event emission |
| `demo_agents/summarizer/agent.py` | Modify | Replace heuristics with LiteLLM call |
| `demo_agents/translator/agent.py` | Modify | Replace heuristics with LiteLLM call |
| `demo_agents/code_reviewer/agent.py` | Modify | Replace heuristics with LiteLLM call |
| `demo_agents/data_analyst/agent.py` | Modify | Replace heuristics with LiteLLM call |
| `demo_agents/research/agent.py` | Modify | Add real discovery + A2A delegation |
| `scripts/seed.py` | Create | Seed users, agents, credits |
| `scripts/demo.sh` | Create | One-command demo launcher |
| `src/models/activity.py` | Create | Activity event model |
| `src/api/routes/activity.py` | Create | SSE activity stream endpoint |
| `frontend/src/components/admin/activity-feed.tsx` | Create | Live activity feed component |
| `frontend/src/app/admin/activity/page.tsx` | Create | Activity page in admin |
| `docker-compose.demo.yml` | Create | Full demo stack |
| `Dockerfile` | Create | Backend container |
| `demo_agents/Dockerfile` | Create | Agent container |

## Success Criteria

1. `bash scripts/demo.sh` starts everything — marketplace has 5 agents, user can login and submit tasks
2. Research Agent discovers + delegates to other agents via real A2A protocol
3. Each agent calls a real LLM (Ollama local = zero cost)
4. Admin dashboard shows live activity feed of the orchestration
5. Credits are charged at each delegation step
6. Total cost to run: $0 (Ollama + SQLite)
7. Same setup can switch to paid LLMs by changing `MODEL` env var
8. Docker Compose deploys the full stack to a cloud URL

## Implementation Order

Phase 1 → Phase 2 → Phase 3 → Phase 4

Each phase is independently demoable. Phase 1+2 gives you a local demo. Phase 3 makes it visually impressive. Phase 4 makes it shareable.
