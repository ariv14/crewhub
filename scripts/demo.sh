#!/usr/bin/env bash
set -euo pipefail

# CrewHub Demo Launcher
# Starts backend, demo agents, seeds data, and opens the browser.
# Usage: bash scripts/demo.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}==>${NC} $1"; }
ok()    { echo -e "${GREEN}==>${NC} $1"; }
warn()  { echo -e "${YELLOW}==>${NC} $1"; }
err()   { echo -e "${RED}==>${NC} $1"; }

# Track PIDs for cleanup
PIDS=()

cleanup() {
    echo ""
    info "Shutting down..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    ok "All processes stopped."
}
trap cleanup EXIT INT TERM

# -------------------------------------------------------------------
# Step 1: Check prerequisites
# -------------------------------------------------------------------

info "Checking prerequisites..."

if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    err "Python 3 is required. Install from https://python.org"
    exit 1
fi
PYTHON=$(command -v python3 || command -v python)

if ! command -v node &>/dev/null; then
    err "Node.js is required. Install from https://nodejs.org"
    exit 1
fi

ok "Python: $($PYTHON --version)"
ok "Node: $(node --version)"

# -------------------------------------------------------------------
# Step 2: Check Ollama (optional but recommended)
# -------------------------------------------------------------------

MODEL="${MODEL:-ollama/llama3.2}"

if [[ "$MODEL" == ollama/* ]]; then
    OLLAMA_MODEL="${MODEL#ollama/}"
    if command -v ollama &>/dev/null; then
        ok "Ollama found"
        if ! ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
            info "Pulling model: $OLLAMA_MODEL (this may take a few minutes)..."
            ollama pull "$OLLAMA_MODEL"
        fi
        ok "Model '$OLLAMA_MODEL' ready"
    else
        warn "Ollama not found. Install from https://ollama.com"
        warn "Agents will use fallback mode (echo input)."
        warn "To use a paid API instead, set MODEL=gpt-4o-mini and OPENAI_API_KEY=..."
    fi
fi

# -------------------------------------------------------------------
# Step 3: Install dependencies
# -------------------------------------------------------------------

info "Installing Python dependencies..."
$PYTHON -m pip install -e ".[dev]" -q 2>/dev/null || $PYTHON -m pip install -e ".[dev]"

if [ -d frontend ]; then
    info "Installing frontend dependencies..."
    (cd frontend && npm install --silent 2>/dev/null || npm install)
fi

# -------------------------------------------------------------------
# Step 4: Set up environment
# -------------------------------------------------------------------

if [ ! -f .env ]; then
    info "Creating .env file..."
    cat > .env << 'ENVEOF'
DEBUG=true
SECRET_KEY=demo-secret-key-at-least-32-characters-long
DATABASE_URL=sqlite+aiosqlite:///./crewhub.db
ENVEOF
    ok "Created .env with SQLite config"
fi

# -------------------------------------------------------------------
# Step 5: Initialize database
# -------------------------------------------------------------------

info "Initializing database..."
$PYTHON -m alembic upgrade head 2>/dev/null || {
    warn "Alembic migration failed, trying direct table creation..."
    $PYTHON -c "
from src.database import engine, Base
from src.models import *
import asyncio
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(init())
print('Database tables created.')
"
}

# -------------------------------------------------------------------
# Step 6: Start backend
# -------------------------------------------------------------------

info "Starting backend API on port 8080..."
$PYTHON -m uvicorn src.main:app --port 8080 --host 0.0.0.0 --log-level warning &
PIDS+=($!)

# Wait for backend
for i in $(seq 1 30); do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        ok "Backend ready at http://localhost:8080"
        break
    fi
    if [ "$i" -eq 30 ]; then
        err "Backend failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# -------------------------------------------------------------------
# Step 7: Run seed script
# -------------------------------------------------------------------

info "Seeding demo data..."
$PYTHON scripts/seed.py --url http://localhost:8080 || warn "Seed script had issues (may be already seeded)"

# -------------------------------------------------------------------
# Step 8: Start demo agents
# -------------------------------------------------------------------

info "Starting 5 demo agents..."
export MODEL
$PYTHON -m demo_agents.run_all &
PIDS+=($!)

# Wait for agents
sleep 3
for port in 8001 8002 8003 8004 8005; do
    if curl -s "http://localhost:$port/.well-known/agent-card.json" > /dev/null 2>&1; then
        ok "Agent on port $port ready"
    else
        warn "Agent on port $port not ready yet"
    fi
done

# -------------------------------------------------------------------
# Step 9: Start frontend (if available)
# -------------------------------------------------------------------

if [ -d frontend ] && [ -f frontend/package.json ]; then
    info "Starting frontend on port 3000..."
    (cd frontend && npm run dev -- --port 3000) &
    PIDS+=($!)
    sleep 3
fi

# -------------------------------------------------------------------
# Step 10: Done
# -------------------------------------------------------------------

FRONTEND_URL="http://localhost:3000"
SWAGGER_URL="http://localhost:8080/docs"

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  CrewHub Demo is Ready!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "  Frontend:     ${BLUE}${FRONTEND_URL}${NC}"
echo -e "  API Docs:     ${BLUE}${SWAGGER_URL}${NC}"
echo -e "  Agent Cards:  ${BLUE}http://localhost:8001/.well-known/agent-card.json${NC}"
echo ""
echo -e "  Demo Login:   demo@crewhub.local / DemoPass123!"
echo -e "  Admin Login:  admin@crewhub.local / AdminPass123!"
echo -e "  LLM Model:    ${MODEL}"
echo ""
echo -e "  Press ${RED}Ctrl+C${NC} to stop everything."
echo ""

# Try to open browser
if command -v open &>/dev/null; then
    open "$FRONTEND_URL" 2>/dev/null || true
elif command -v xdg-open &>/dev/null; then
    xdg-open "$FRONTEND_URL" 2>/dev/null || true
fi

# Wait for all background processes
wait
