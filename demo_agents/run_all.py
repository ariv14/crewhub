#!/usr/bin/env python3
"""Start all 5 demo agents and optionally register them with the marketplace.

Usage:
    python -m demo_agents.run_all                    # start all agents
    python -m demo_agents.run_all --register         # start + register with marketplace
    python -m demo_agents.run_all --register-only    # register without starting
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time

import httpx

# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------

AGENTS = [
    {
        "module": "demo_agents.summarizer.agent:app",
        "port": 8001,
        "name": "Text Summarizer",
        "description": "Summarizes text and extracts key points using an LLM.",
        "version": "1.0.0",
        "endpoint": "http://localhost:8001",
        "category": "text",
        "tags": ["summarization", "nlp", "text-processing"],
        "credits": 1,
        "skills": [
            {
                "skill_key": "summarize",
                "name": "Summarize Text",
                "description": "Produce a concise extractive summary of the input text.",
                "input_modes": ["text"],
                "output_modes": ["text"],
                "avg_credits": 1,
                "avg_latency_ms": 100,
            },
            {
                "skill_key": "extract-key-points",
                "name": "Extract Key Points",
                "description": "Return a bullet-point list of key takeaways.",
                "input_modes": ["text"],
                "output_modes": ["text"],
                "avg_credits": 1,
                "avg_latency_ms": 100,
            },
        ],
    },
    {
        "module": "demo_agents.translator.agent:app",
        "port": 8002,
        "name": "Universal Translator",
        "description": "Translates text between languages using an LLM.",
        "version": "1.0.0",
        "endpoint": "http://localhost:8002",
        "category": "translation",
        "tags": ["translation", "nlp", "multilingual"],
        "credits": 2,
        "skills": [
            {
                "skill_key": "translate",
                "name": "Translate Text",
                "description": "Translate text from one language to another.",
                "input_modes": ["text"],
                "output_modes": ["text"],
                "avg_credits": 2,
                "avg_latency_ms": 200,
            },
        ],
    },
    {
        "module": "demo_agents.code_reviewer.agent:app",
        "port": 8003,
        "name": "Python Code Reviewer",
        "description": "Reviews code for quality issues and suggests improvements using an LLM.",
        "version": "1.0.0",
        "endpoint": "http://localhost:8003",
        "category": "development",
        "tags": ["python", "code-review", "static-analysis", "linting"],
        "credits": 3,
        "skills": [
            {
                "skill_key": "review-code",
                "name": "Review Python Code",
                "description": "Analyse Python source code for common quality issues.",
                "input_modes": ["text"],
                "output_modes": ["text", "data"],
                "avg_credits": 3,
                "avg_latency_ms": 150,
            },
            {
                "skill_key": "suggest-improvements",
                "name": "Suggest Code Improvements",
                "description": "Return actionable improvement suggestions for Python code.",
                "input_modes": ["text"],
                "output_modes": ["text"],
                "avg_credits": 3,
                "avg_latency_ms": 150,
            },
        ],
    },
    {
        "module": "demo_agents.data_analyst.agent:app",
        "port": 8004,
        "name": "Data Analyst",
        "description": "Analyzes CSV data and computes summary statistics using an LLM.",
        "version": "1.0.0",
        "endpoint": "http://localhost:8004",
        "category": "data",
        "tags": ["csv", "data-analysis", "statistics"],
        "credits": 5,
        "skills": [
            {
                "skill_key": "analyze-csv",
                "name": "Analyze CSV Data",
                "description": "Parse CSV text and return a structural overview.",
                "input_modes": ["text"],
                "output_modes": ["text", "data"],
                "avg_credits": 5,
                "avg_latency_ms": 300,
            },
            {
                "skill_key": "generate-summary-stats",
                "name": "Generate Summary Statistics",
                "description": "Compute mean, median, std, min, max for numeric columns.",
                "input_modes": ["text"],
                "output_modes": ["text", "data"],
                "avg_credits": 5,
                "avg_latency_ms": 300,
            },
        ],
    },
    {
        "module": "demo_agents.research_agent.agent:app",
        "port": 8005,
        "name": "Research Agent",
        "description": "Researches topics and compiles reports using an LLM. Demonstrates A2A delegation.",
        "version": "1.0.0",
        "endpoint": "http://localhost:8005",
        "category": "research",
        "tags": ["research", "report", "a2a-delegation"],
        "credits": 10,
        "skills": [
            {
                "skill_key": "research-topic",
                "name": "Research Topic",
                "description": "Research a topic and compile a structured report with optional translation delegation.",
                "input_modes": ["text"],
                "output_modes": ["text"],
                "avg_credits": 10,
                "avg_latency_ms": 2000,
            },
        ],
    },
]

MARKETPLACE_API = os.environ.get("CREWHUB_API_URL", "http://localhost:8080") + "/api/v1"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_agents(api_key: str | None = None):
    """Register all demo agents with the marketplace API."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    registered = 0
    for agent in AGENTS:
        payload = {
            "name": agent["name"],
            "description": agent["description"],
            "version": agent["version"],
            "endpoint": agent["endpoint"],
            "capabilities": {"streaming": False, "pushNotifications": False},
            "skills": agent["skills"],
            "security_schemes": [],
            "category": agent["category"],
            "tags": agent["tags"],
            "pricing": {"model": "per_task", "credits": agent["credits"]},
        }

        try:
            resp = httpx.post(
                f"{MARKETPLACE_API}/agents/",
                json=payload,
                headers=headers,
                timeout=10.0,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                print(f"  [OK] Registered '{agent['name']}' (id={data.get('id', 'N/A')})")
                registered += 1
            elif resp.status_code == 409:
                print(f"  [SKIP] '{agent['name']}' already registered")
                registered += 1
            else:
                print(f"  [FAIL] '{agent['name']}': {resp.status_code} - {resp.text[:200]}")
        except httpx.HTTPError as exc:
            print(f"  [FAIL] '{agent['name']}': {exc}")

    print(f"\nRegistered {registered}/{len(AGENTS)} agents.")
    return registered


# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------

def start_all_agents() -> list[subprocess.Popen]:
    """Start all demo agents as uvicorn subprocesses."""
    processes: list[subprocess.Popen] = []
    for agent in AGENTS:
        cmd = [
            sys.executable, "-m", "uvicorn",
            agent["module"],
            "--port", str(agent["port"]),
            "--host", "0.0.0.0",
            "--log-level", "info",
        ]
        print(f"  Starting {agent['name']} on port {agent['port']}...")
        proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
        processes.append(proc)
    return processes


def wait_for_agents(timeout: float = 15.0):
    """Wait until all agents respond to health checks."""
    start = time.time()
    for agent in AGENTS:
        url = f"{agent['endpoint']}/.well-known/agent-card.json"
        while time.time() - start < timeout:
            try:
                resp = httpx.get(url, timeout=2.0)
                if resp.status_code == 200:
                    print(f"  [READY] {agent['name']} at {agent['endpoint']}")
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        else:
            print(f"  [TIMEOUT] {agent['name']} did not start within {timeout}s")


def shutdown_all(processes: list[subprocess.Popen]):
    """Gracefully shut down all agent processes."""
    print("\nShutting down demo agents...")
    for proc in processes:
        proc.send_signal(signal.SIGTERM)
    for proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    print("All agents stopped.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run all A2A demo agents")
    parser.add_argument(
        "--register",
        action="store_true",
        help="Register agents with the marketplace after starting",
    )
    parser.add_argument(
        "--register-only",
        action="store_true",
        help="Only register agents (assumes they are already running)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for marketplace authentication",
    )
    args = parser.parse_args()

    if args.register_only:
        print("Registering demo agents with marketplace...")
        register_agents(api_key=args.api_key)
        return

    print("Starting demo agents...\n")
    processes = start_all_agents()

    # Set up graceful shutdown
    def signal_handler(sig, frame):
        shutdown_all(processes)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("\nWaiting for agents to be ready...\n")
    wait_for_agents()

    if args.register:
        print("\nRegistering agents with marketplace...\n")
        register_agents(api_key=args.api_key)

    print("\n" + "=" * 60)
    print("All demo agents are running!")
    print("=" * 60)
    print()
    for agent in AGENTS:
        print(f"  {agent['name']:25s}  {agent['endpoint']}")
    print()
    print("Press Ctrl+C to stop all agents.")
    print()

    # Wait for all processes
    try:
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        shutdown_all(processes)


if __name__ == "__main__":
    main()
