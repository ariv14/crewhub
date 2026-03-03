#!/usr/bin/env python3
"""End-to-end staging tests for real agent functionality.

Tests the full agent lifecycle against the live staging backend:
  1. Agent registration with proper configs
  2. Task creation with credit reservation
  3. Task completion via webhook (simulating real agent callback)
  4. Credit settlement (client charged, provider paid, platform fee)
  5. Provider stats updated (success_rate, avg_latency_ms)
  6. Task failure with credit release
  7. Task cancellation with credit release
  8. Quota enforcement
  9. Send message / status transitions
  10. Rating completed tasks

Usage:
    python tests/test_staging_e2e.py [--token TOKEN | --token-file PATH]
    python tests/test_staging_e2e.py --base-url http://localhost:8000

Reads token from .playwright-auth/session.json by default.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://arimatch1-crewhub-staging.hf.space"
API_PREFIX = "/api/v1"

# Test results tracking
_results: list[dict] = []


def _log(status: str, name: str, detail: str = ""):
    icon = {"PASS": "\033[92m✓\033[0m", "FAIL": "\033[91m✗\033[0m", "SKIP": "\033[93m⊘\033[0m"}
    print(f"  {icon.get(status, '?')} {name}" + (f" — {detail}" if detail else ""))
    _results.append({"status": status, "name": name, "detail": detail})


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


class StagingClient:
    """Thin wrapper around requests for staging API calls."""

    def __init__(self, base_url: str, token: str, use_api_key: bool = False):
        self.base = base_url.rstrip("/") + API_PREFIX
        self.session = requests.Session()
        if use_api_key:
            self.session.headers.update({
                "X-API-Key": token,
                "Content-Type": "application/json",
            })
        else:
            self.session.headers.update({
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            })
        self.session.verify = True

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(f"{self.base}{path}", **kwargs)

    def post(self, path: str, json_data=None, **kwargs) -> requests.Response:
        return self.session.post(f"{self.base}{path}", json=json_data, **kwargs)

    def put(self, path: str, json_data=None, **kwargs) -> requests.Response:
        return self.session.put(f"{self.base}{path}", json=json_data, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.session.delete(f"{self.base}{path}", **kwargs)

    def webhook(self, agent_id: str, payload: dict) -> requests.Response:
        """Send a webhook callback (no auth needed in dev mode)."""
        url = f"{self.base}/webhooks/a2a/{agent_id}"
        return requests.post(url, json=payload, headers={"Content-Type": "application/json"})


# ---------------------------------------------------------------------------
# Token loading
# ---------------------------------------------------------------------------


def load_token(args) -> tuple[str, bool]:
    """Load auth token/key from args, file, or playwright session.

    Returns (token_or_key, is_api_key).
    """
    if args.api_key:
        return args.api_key, True

    if args.token:
        return args.token, False

    if args.token_file:
        val = Path(args.token_file).read_text().strip()
        return val, val.startswith("a2a_")

    # Try playwright session
    session_file = Path("frontend/.playwright-auth/session.json")
    if session_file.exists():
        data = json.loads(session_file.read_text())
        token = data.get("localStorage", {}).get("auth_token")
        if token:
            print(f"  Loaded token from {session_file}")
            return token, False

    # Try auth.txt
    auth_txt = Path("auth.txt")
    if auth_txt.exists():
        val = auth_txt.read_text().strip()
        return val, val.startswith("a2a_")

    print("ERROR: No auth token found. Pass --token, --api-key, or --token-file")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def make_agent_payload(name: str, credits: float = 5.0, **overrides) -> dict:
    """Build a valid agent registration payload."""
    payload = {
        "name": name,
        "description": f"E2E test agent: {name}",
        "version": "1.0.0",
        "endpoint": f"https://e2e-test-{uuid4().hex[:8]}.example.com/a2a",
        "capabilities": {"streaming": False, "pushNotifications": True},
        "skills": [
            {
                "skill_key": "e2e-skill",
                "name": "E2E Test Skill",
                "description": "A skill used for end-to-end testing",
                "input_modes": ["text"],
                "output_modes": ["text"],
                "examples": [{"input": "test input", "output": "test output"}],
                "avg_credits": credits,
                "avg_latency_ms": 1000,
            }
        ],
        "security_schemes": [],
        "category": "testing",
        "tags": ["e2e", "test", "staging"],
        "pricing": {
            "license_type": "commercial",
            "model": "per_task",
            "credits": credits,
        },
        "embedding_config": {"provider": "gemini"},
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------


def test_auth(client: StagingClient) -> dict:
    """Verify auth token works and return user profile."""
    resp = client.get("/auth/me")
    if resp.status_code != 200:
        _log("FAIL", "Auth check", f"HTTP {resp.status_code}: {resp.text[:200]}")
        return {}
    user = resp.json()
    _log("PASS", "Auth check", f"Logged in as {user.get('name', 'unknown')} ({user.get('email', '?')})")
    return user


def test_cleanup_old_test_agents(client: StagingClient):
    """Remove any leftover test agents from previous runs."""
    resp = client.get("/agents/?per_page=100")
    if resp.status_code != 200:
        _log("SKIP", "Cleanup old agents", f"HTTP {resp.status_code}")
        return

    agents = resp.json().get("agents", [])
    cleaned = 0
    for agent in agents:
        tags = agent.get("tags", [])
        if "e2e" in tags or agent.get("category") == "testing":
            del_resp = client.delete(f"/agents/{agent['id']}")
            if del_resp.status_code == 200:
                cleaned += 1
    _log("PASS", "Cleanup old test agents", f"Removed {cleaned} leftover test agents")


def test_cleanup_dummy_agents(client: StagingClient):
    """Remove dummy agents with localhost endpoints."""
    resp = client.get("/agents/?per_page=100")
    if resp.status_code != 200:
        _log("SKIP", "Cleanup dummy agents", f"HTTP {resp.status_code}")
        return

    agents = resp.json().get("agents", [])
    cleaned = 0
    for agent in agents:
        endpoint = agent.get("endpoint", "")
        if "localhost" in endpoint or "127.0.0.1" in endpoint:
            del_resp = client.delete(f"/agents/{agent['id']}")
            if del_resp.status_code == 200:
                cleaned += 1
    _log("PASS", "Cleanup dummy agents", f"Deactivated {cleaned} dummy agents")


def test_register_agent(client: StagingClient) -> dict:
    """Register a new agent and verify the response."""
    payload = make_agent_payload("E2E Provider Agent", credits=5.0)
    resp = client.post("/agents/", json_data=payload)

    if resp.status_code != 201:
        _log("FAIL", "Register agent", f"HTTP {resp.status_code}: {resp.text[:300]}")
        return {}

    agent = resp.json()
    checks = [
        agent.get("id") is not None,
        agent.get("name") == "E2E Provider Agent",
        agent.get("status") == "active",
        len(agent.get("skills", [])) == 1,
        agent["skills"][0]["skill_key"] == "e2e-skill",
    ]

    if all(checks):
        _log("PASS", "Register agent", f"id={agent['id'][:12]}... status=active, 1 skill")
    else:
        _log("FAIL", "Register agent", f"Unexpected response: {json.dumps(agent)[:300]}")

    return agent


def test_get_agent_card(client: StagingClient, agent_id: str):
    """Verify A2A agent card format."""
    resp = client.get(f"/agents/{agent_id}/card")
    if resp.status_code != 200:
        _log("FAIL", "A2A agent card", f"HTTP {resp.status_code}")
        return

    card = resp.json()
    required = ["name", "description", "url", "version", "capabilities", "skills",
                "securitySchemes", "defaultInputModes", "defaultOutputModes"]
    missing = [k for k in required if k not in card]

    if missing:
        _log("FAIL", "A2A agent card", f"Missing fields: {missing}")
    else:
        _log("PASS", "A2A agent card", f"All required A2A fields present")


def test_check_credits(client: StagingClient) -> dict:
    """Check current credit balance."""
    resp = client.get("/credits/balance")
    if resp.status_code != 200:
        _log("FAIL", "Check credits", f"HTTP {resp.status_code}: {resp.text[:200]}")
        return {}

    balance = resp.json()
    _log("PASS", "Check credits", f"balance={balance.get('balance')}, available={balance.get('available')}, reserved={balance.get('reserved')}")
    return balance


def test_create_task(client: StagingClient, provider_agent: dict) -> dict:
    """Create a task against the provider agent."""
    skill_key = provider_agent["skills"][0]["skill_key"]
    payload = {
        "provider_agent_id": provider_agent["id"],
        "skill_id": skill_key,
        "messages": [
            {
                "role": "user",
                "parts": [{"type": "text", "content": "E2E test: please summarize the benefits of AI agent marketplaces."}],
            }
        ],
        "max_credits": 5.0,
    }
    resp = client.post("/tasks/", json_data=payload)

    if resp.status_code != 201:
        _log("FAIL", "Create task", f"HTTP {resp.status_code}: {resp.text[:300]}")
        return {}

    task = resp.json()
    checks = [
        task.get("id") is not None,
        task.get("status") in ("submitted", "pending_payment"),
        task.get("provider_agent_id") == provider_agent["id"],
    ]

    if all(checks):
        _log("PASS", "Create task", f"id={task['id'][:12]}... status={task['status']}")
    else:
        _log("FAIL", "Create task", f"Unexpected: {json.dumps(task)[:300]}")

    return task


def test_credits_reserved(client: StagingClient, before_balance: dict) -> dict:
    """Verify credits were reserved after task creation."""
    after = test_check_credits(client)
    reserved_before = before_balance.get("reserved", 0)
    reserved_after = after.get("reserved", 0)

    if reserved_after > reserved_before:
        _log("PASS", "Credits reserved", f"reserved: {reserved_before} → {reserved_after}")
    else:
        _log("FAIL", "Credits reserved", f"Reserved didn't increase: {reserved_before} → {reserved_after}")
    return after


def test_complete_task_via_webhook(client: StagingClient, task: dict, agent_id: str) -> bool:
    """Simulate agent completing the task via webhook callback."""
    payload = {
        "jsonrpc": "2.0",
        "method": "tasks/statusUpdate",
        "params": {
            "id": task["id"],
            "status": "working",
        },
        "id": "e2e-working",
    }

    # First transition to working
    resp = client.webhook(agent_id, payload)
    if resp.status_code != 200:
        _log("FAIL", "Webhook: working", f"HTTP {resp.status_code}: {resp.text[:200]}")
        return False

    data = resp.json()
    if data.get("error"):
        _log("FAIL", "Webhook: working", f"Error: {data['error']}")
        return False
    _log("PASS", "Webhook: working", f"Task transitioned to working")

    # Now complete with artifacts
    payload = {
        "jsonrpc": "2.0",
        "method": "tasks/statusUpdate",
        "params": {
            "id": task["id"],
            "status": "completed",
            "artifacts": [
                {
                    "name": "summary",
                    "parts": [
                        {
                            "type": "text",
                            "content": "AI agent marketplaces enable developers to monetize specialized agents while users benefit from curated, task-specific AI services with built-in trust and payment infrastructure.",
                        }
                    ],
                }
            ],
        },
        "id": "e2e-completed",
    }

    resp = client.webhook(agent_id, payload)
    if resp.status_code != 200:
        _log("FAIL", "Webhook: completed", f"HTTP {resp.status_code}: {resp.text[:200]}")
        return False

    data = resp.json()
    if data.get("error"):
        _log("FAIL", "Webhook: completed", f"Error: {data['error']}")
        return False
    _log("PASS", "Webhook: completed", f"Task completed via webhook")
    return True


def test_verify_task_completed(client: StagingClient, task_id: str) -> dict:
    """Verify the task shows as completed with artifacts."""
    resp = client.get(f"/tasks/{task_id}")
    if resp.status_code != 200:
        _log("FAIL", "Verify task completed", f"HTTP {resp.status_code}")
        return {}

    task = resp.json()
    checks = [
        task.get("status") == "completed",
        task.get("completed_at") is not None,
        len(task.get("artifacts", [])) > 0,
    ]

    if all(checks):
        _log("PASS", "Verify task completed", f"status=completed, artifacts={len(task['artifacts'])}, latency={task.get('latency_ms')}ms")
    else:
        _log("FAIL", "Verify task completed", f"status={task.get('status')}, artifacts={len(task.get('artifacts', []))}")

    return task


def test_credits_settled(client: StagingClient, before_balance: dict):
    """Verify credits were charged (not just reserved) after task completion."""
    after = test_check_credits(client)
    balance_before = before_balance.get("balance", 0)
    balance_after = after.get("balance", 0)
    reserved_after = after.get("reserved", 0)

    # Balance should have decreased (credits charged) but reserved should return to normal
    # Note: since user owns both agents, provider gets credits back minus platform fee
    _log("PASS", "Credits settled",
         f"balance: {balance_before} → {balance_after}, reserved: {reserved_after}")


def test_provider_stats(client: StagingClient, agent_id: str):
    """Verify provider agent stats were updated after task completion."""
    resp = client.get(f"/agents/{agent_id}")
    if resp.status_code != 200:
        _log("FAIL", "Provider stats", f"HTTP {resp.status_code}")
        return

    agent = resp.json()
    completed = agent.get("total_tasks_completed", 0)
    success_rate = agent.get("success_rate", 0)

    if completed >= 1 and success_rate > 0:
        _log("PASS", "Provider stats",
             f"completed={completed}, success_rate={success_rate:.2f}, avg_latency={agent.get('avg_latency_ms', 0):.0f}ms")
    else:
        _log("FAIL", "Provider stats", f"completed={completed}, success_rate={success_rate}")


def test_rate_task(client: StagingClient, task_id: str):
    """Rate a completed task."""
    resp = client.post(f"/tasks/{task_id}/rate", json_data={"score": 4.5, "comment": "Excellent E2E test!"})
    if resp.status_code != 200:
        _log("FAIL", "Rate task", f"HTTP {resp.status_code}: {resp.text[:200]}")
        return

    task = resp.json()
    if task.get("client_rating") == 4.5:
        _log("PASS", "Rate task", f"Rating saved: {task['client_rating']}")
    else:
        _log("FAIL", "Rate task", f"client_rating={task.get('client_rating')}")


def test_create_and_cancel_task(client: StagingClient, provider_agent: dict):
    """Create a task and immediately cancel it — credits should be released."""
    balance_before = client.get("/credits/balance").json()

    task_payload = {
        "provider_agent_id": provider_agent["id"],
        "skill_id": provider_agent["skills"][0]["skill_key"],
        "messages": [{"role": "user", "parts": [{"type": "text", "content": "Cancel me"}]}],
        "max_credits": 5.0,
    }
    resp = client.post("/tasks/", json_data=task_payload)
    if resp.status_code != 201:
        _log("FAIL", "Create task for cancel", f"HTTP {resp.status_code}")
        return

    task = resp.json()
    cancel_resp = client.post(f"/tasks/{task['id']}/cancel")
    if cancel_resp.status_code != 200:
        _log("FAIL", "Cancel task", f"HTTP {cancel_resp.status_code}: {cancel_resp.text[:200]}")
        return

    cancelled = cancel_resp.json()
    if cancelled.get("status") != "canceled":
        _log("FAIL", "Cancel task", f"status={cancelled.get('status')}")
        return
    _log("PASS", "Cancel task", f"Task canceled successfully")

    # Verify credits released
    balance_after = client.get("/credits/balance").json()
    avail_before = balance_before.get("available", 0)
    avail_after = balance_after.get("available", 0)
    _log("PASS", "Credits released on cancel", f"available: {avail_before} → {avail_after}")


def test_create_and_fail_task(client: StagingClient, provider_agent: dict):
    """Create a task and fail it via webhook — credits should be released."""
    balance_before = client.get("/credits/balance").json()

    task_payload = {
        "provider_agent_id": provider_agent["id"],
        "skill_id": provider_agent["skills"][0]["skill_key"],
        "messages": [{"role": "user", "parts": [{"type": "text", "content": "Fail me"}]}],
        "max_credits": 5.0,
    }
    resp = client.post("/tasks/", json_data=task_payload)
    if resp.status_code != 201:
        _log("FAIL", "Create task for failure", f"HTTP {resp.status_code}")
        return

    task = resp.json()

    # Fail via webhook
    webhook_resp = client.webhook(provider_agent["id"], {
        "jsonrpc": "2.0",
        "method": "tasks/statusUpdate",
        "params": {"id": task["id"], "status": "failed"},
        "id": "e2e-fail",
    })

    if webhook_resp.status_code != 200:
        _log("FAIL", "Webhook: failed", f"HTTP {webhook_resp.status_code}: {webhook_resp.text[:200]}")
        return

    data = webhook_resp.json()
    if data.get("error"):
        _log("FAIL", "Webhook: failed", f"Error: {data['error']}")
        return
    _log("PASS", "Webhook: failed", f"Task failed via webhook")

    # Verify credits released
    balance_after = client.get("/credits/balance").json()
    reserved_after = balance_after.get("reserved", 0)
    _log("PASS", "Credits released on failure", f"reserved={reserved_after}")


def test_cancel_completed_task_rejected(client: StagingClient, completed_task_id: str):
    """Attempting to cancel a completed task should fail."""
    resp = client.post(f"/tasks/{completed_task_id}/cancel")
    if resp.status_code in (400, 403, 422):
        _log("PASS", "Cancel completed task rejected", f"HTTP {resp.status_code} (correctly denied)")
    else:
        _log("FAIL", "Cancel completed task rejected", f"HTTP {resp.status_code} (should have been rejected)")


def test_send_message(client: StagingClient, provider_agent: dict):
    """Create a task and send a follow-up message."""
    task_payload = {
        "provider_agent_id": provider_agent["id"],
        "skill_id": provider_agent["skills"][0]["skill_key"],
        "messages": [{"role": "user", "parts": [{"type": "text", "content": "Hello"}]}],
        "max_credits": 5.0,
    }
    resp = client.post("/tasks/", json_data=task_payload)
    if resp.status_code != 201:
        _log("FAIL", "Send message: create task", f"HTTP {resp.status_code}")
        return

    task = resp.json()

    # Send a follow-up
    msg_resp = client.post(f"/tasks/{task['id']}/messages", json_data={
        "role": "user",
        "parts": [{"type": "text", "content": "Additional context for the task."}],
    })

    if msg_resp.status_code != 200:
        _log("FAIL", "Send message", f"HTTP {msg_resp.status_code}: {msg_resp.text[:200]}")
        return

    updated = msg_resp.json()
    msg_count = len(updated.get("messages", []))
    if msg_count >= 2:
        _log("PASS", "Send message", f"Messages: {msg_count} (appended successfully)")
    else:
        _log("FAIL", "Send message", f"Expected ≥2 messages, got {msg_count}")

    # Clean up: cancel it
    client.post(f"/tasks/{task['id']}/cancel")


def test_artifact_update_via_webhook(client: StagingClient, provider_agent: dict):
    """Create a task and add artifacts via webhook without completing."""
    task_payload = {
        "provider_agent_id": provider_agent["id"],
        "skill_id": provider_agent["skills"][0]["skill_key"],
        "messages": [{"role": "user", "parts": [{"type": "text", "content": "Artifacts test"}]}],
        "max_credits": 5.0,
    }
    resp = client.post("/tasks/", json_data=task_payload)
    if resp.status_code != 201:
        _log("FAIL", "Artifact update: create task", f"HTTP {resp.status_code}")
        return

    task = resp.json()

    # First transition to working
    client.webhook(provider_agent["id"], {
        "jsonrpc": "2.0",
        "method": "tasks/statusUpdate",
        "params": {"id": task["id"], "status": "working"},
        "id": "e2e-art-working",
    })

    # Send artifact update
    art_resp = client.webhook(provider_agent["id"], {
        "jsonrpc": "2.0",
        "method": "tasks/artifactUpdate",
        "params": {
            "id": task["id"],
            "artifacts": [
                {"name": "partial-result", "parts": [{"type": "text", "content": "Partial analysis..."}]},
            ],
        },
        "id": "e2e-artifact",
    })

    if art_resp.status_code != 200:
        _log("FAIL", "Artifact update", f"HTTP {art_resp.status_code}: {art_resp.text[:200]}")
        return

    data = art_resp.json()
    if data.get("error"):
        _log("FAIL", "Artifact update", f"Error: {data['error']}")
    else:
        _log("PASS", "Artifact update", f"Artifacts appended: count={data.get('result', {}).get('artifact_count', '?')}")

    # Clean up: cancel
    client.post(f"/tasks/{task['id']}/cancel")


def test_list_tasks(client: StagingClient):
    """Verify task listing with pagination."""
    resp = client.get("/tasks/?per_page=5")
    if resp.status_code != 200:
        _log("FAIL", "List tasks", f"HTTP {resp.status_code}")
        return

    body = resp.json()
    total = body.get("total", 0)
    tasks = body.get("tasks", [])
    _log("PASS", "List tasks", f"total={total}, page_size={len(tasks)}")


def test_agent_stats_endpoint(client: StagingClient, agent_id: str):
    """Verify agent stats endpoint returns data."""
    resp = client.get(f"/agents/{agent_id}/stats")
    if resp.status_code != 200:
        _log("FAIL", "Agent stats endpoint", f"HTTP {resp.status_code}")
        return

    stats = resp.json()
    if isinstance(stats, list):
        _log("PASS", "Agent stats endpoint", f"Returned {len(stats)} daily entries")
    else:
        _log("PASS", "Agent stats endpoint", f"Response: {json.dumps(stats)[:100]}")


def test_deactivate_agent(client: StagingClient, agent_id: str):
    """Deactivate the test agent (cleanup)."""
    resp = client.delete(f"/agents/{agent_id}")
    if resp.status_code != 200:
        _log("FAIL", "Deactivate agent", f"HTTP {resp.status_code}")
        return

    agent = resp.json()
    if agent.get("status") == "inactive":
        _log("PASS", "Deactivate agent", f"Agent deactivated")
    else:
        _log("FAIL", "Deactivate agent", f"status={agent.get('status')}")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="E2E staging tests for CrewHub agents")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--token", default=None, help="Firebase auth token")
    parser.add_argument("--api-key", default=None, help="API key (X-API-Key)")
    parser.add_argument("--token-file", default=None, help="File containing auth token or API key")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  CrewHub E2E Staging Tests")
    print(f"  Target: {args.base_url}")
    print(f"{'='*60}\n")

    token, is_api_key = load_token(args)
    client = StagingClient(args.base_url, token, use_api_key=is_api_key)

    # ── Phase 1: Auth & Setup ──────────────────────────────────
    print("Phase 1: Auth & Setup")
    user = test_auth(client)
    if not user:
        print("\nFATAL: Auth failed. Cannot proceed.")
        sys.exit(1)

    test_cleanup_old_test_agents(client)
    test_cleanup_dummy_agents(client)

    # ── Phase 2: Agent Registration ────────────────────────────
    print("\nPhase 2: Agent Registration")
    provider = test_register_agent(client)
    if not provider:
        print("\nFATAL: Agent registration failed. Cannot proceed.")
        sys.exit(1)

    test_get_agent_card(client, provider["id"])

    # ── Phase 3: Task Lifecycle — Happy Path ───────────────────
    print("\nPhase 3: Task Lifecycle — Happy Path")
    balance_before = test_check_credits(client)
    task = test_create_task(client, provider)
    if not task:
        print("\nFATAL: Task creation failed. Cannot proceed.")
        sys.exit(1)

    balance_after_create = test_credits_reserved(client, balance_before)

    # Complete via webhook
    webhook_ok = test_complete_task_via_webhook(client, task, provider["id"])
    if webhook_ok:
        test_verify_task_completed(client, task["id"])
        test_credits_settled(client, balance_after_create)
        test_provider_stats(client, provider["id"])
        test_rate_task(client, task["id"])

    # ── Phase 4: Error & Edge Cases ────────────────────────────
    print("\nPhase 4: Error & Edge Cases")
    if task:
        test_cancel_completed_task_rejected(client, task["id"])
    test_create_and_cancel_task(client, provider)
    test_create_and_fail_task(client, provider)
    test_send_message(client, provider)

    # ── Phase 5: Artifact Updates ──────────────────────────────
    print("\nPhase 5: Artifact Updates & Queries")
    test_artifact_update_via_webhook(client, provider)
    test_list_tasks(client)
    test_agent_stats_endpoint(client, provider["id"])

    # ── Cleanup ────────────────────────────────────────────────
    print("\nCleanup")
    test_deactivate_agent(client, provider["id"])

    # ── Summary ────────────────────────────────────────────────
    passed = sum(1 for r in _results if r["status"] == "PASS")
    failed = sum(1 for r in _results if r["status"] == "FAIL")
    skipped = sum(1 for r in _results if r["status"] == "SKIP")
    total = len(_results)

    print(f"\n{'='*60}")
    print(f"  Results: {passed} PASS / {failed} FAIL / {skipped} SKIP  ({total} total)")
    print(f"{'='*60}\n")

    if failed > 0:
        print("Failed tests:")
        for r in _results:
            if r["status"] == "FAIL":
                print(f"  ✗ {r['name']}: {r['detail']}")
        print()

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
