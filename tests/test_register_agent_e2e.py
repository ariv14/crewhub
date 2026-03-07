#!/usr/bin/env python3
"""E2E tests for the register-agent developer flow.

Tests the detect → register → verify → cleanup lifecycle against staging.

Usage:
    python tests/test_register_agent_e2e.py --api-key <key>
    python tests/test_register_agent_e2e.py --base-url http://localhost:8000 --api-key <key>
"""

import argparse
import json
import sys
from uuid import uuid4

import requests

DEFAULT_BASE_URL = "https://arimatch1-crewhub-staging.hf.space"
API_PREFIX = "/api/v1"

SUMMARIZER_URL = "https://arimatch1-crewhub-agent-summarizer.hf.space"
TRANSLATOR_URL = "https://arimatch1-crewhub-agent-translator.hf.space"

_results: list[dict] = []


def _log(status: str, name: str, detail: str = ""):
    icon = {"PASS": "\033[92m✓\033[0m", "FAIL": "\033[91m✗\033[0m", "SKIP": "\033[93m⊘\033[0m"}
    print(f"  {icon.get(status, '?')} {name}" + (f" — {detail}" if detail else ""))
    _results.append({"status": status, "name": name, "detail": detail})


class Client:
    def __init__(self, base_url: str, api_key: str):
        self.base = base_url.rstrip("/") + API_PREFIX
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        })

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(f"{self.base}{path}", **kwargs)

    def post(self, path: str, json_data=None) -> requests.Response:
        return self.session.post(f"{self.base}{path}", json=json_data)

    def delete(self, path: str) -> requests.Response:
        return self.session.delete(f"{self.base}{path}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_detect_summarizer(client: Client) -> dict:
    """Detect agent from summarizer endpoint."""
    resp = client.post("/agents/detect", json_data={"url": SUMMARIZER_URL})
    if resp.status_code != 200:
        _log("FAIL", "Detect summarizer", f"HTTP {resp.status_code}: {resp.text[:200]}")
        return {}

    data = resp.json()
    checks = [
        data.get("name"),
        data.get("card_url", "").endswith("agent-card.json"),
        len(data.get("skills", [])) > 0,
        "suggested_registration" in data,
    ]
    if all(checks):
        _log("PASS", "Detect summarizer",
             f"name={data['name']}, skills={len(data['skills'])}, warnings={data.get('warnings', [])}")
    else:
        _log("FAIL", "Detect summarizer", f"Unexpected: {json.dumps(data)[:300]}")
    return data


def test_detect_translator(client: Client) -> dict:
    """Detect agent from translator endpoint."""
    resp = client.post("/agents/detect", json_data={"url": TRANSLATOR_URL})
    if resp.status_code != 200:
        _log("FAIL", "Detect translator", f"HTTP {resp.status_code}: {resp.text[:200]}")
        return {}

    data = resp.json()
    if data.get("name") and len(data.get("skills", [])) > 0:
        _log("PASS", "Detect translator",
             f"name={data['name']}, skills={len(data['skills'])}")
    else:
        _log("FAIL", "Detect translator", f"Missing name/skills: {json.dumps(data)[:300]}")
    return data


def test_detect_invalid_url(client: Client):
    """Detect with unreachable URL returns 400."""
    resp = client.post("/agents/detect", json_data={"url": "https://nonexistent-agent.invalid"})
    if resp.status_code == 400:
        _log("PASS", "Detect invalid URL", f"400: {resp.json().get('detail', '')}")
    else:
        _log("FAIL", "Detect invalid URL", f"Expected 400, got {resp.status_code}")


def test_detect_response_schema(client: Client):
    """Verify detect response has all required fields."""
    resp = client.post("/agents/detect", json_data={"url": SUMMARIZER_URL})
    if resp.status_code != 200:
        _log("FAIL", "Detect schema", f"HTTP {resp.status_code}")
        return

    data = resp.json()
    required = ["name", "description", "url", "version", "capabilities",
                 "skills", "suggested_registration", "card_url", "warnings"]
    missing = [k for k in required if k not in data]
    if missing:
        _log("FAIL", "Detect schema", f"Missing: {missing}")
    else:
        _log("PASS", "Detect schema", "All required fields present")

    # Check suggested_registration has AgentCreate-compatible fields
    reg = data.get("suggested_registration", {})
    reg_required = ["name", "endpoint", "skills", "pricing", "category"]
    reg_missing = [k for k in reg_required if k not in reg]
    if reg_missing:
        _log("FAIL", "Detect registration payload", f"Missing: {reg_missing}")
    else:
        _log("PASS", "Detect registration payload", "AgentCreate-compatible")


def test_register_from_detect(client: Client, detect_result: dict) -> str | None:
    """Register agent using detected suggested_registration payload.

    Uses a unique endpoint to avoid 409 conflicts with already-registered agents.
    Returns the agent ID on success, None on failure.
    """
    if not detect_result:
        _log("SKIP", "Register from detect", "No detect result")
        return None

    payload = dict(detect_result["suggested_registration"])
    # Use a unique endpoint so we don't conflict with the real registered agent
    unique_suffix = uuid4().hex[:8]
    payload["endpoint"] = f"https://e2e-register-test-{unique_suffix}.example.com"
    payload["name"] = f"E2E Register Test {unique_suffix}"
    resp = client.post("/agents/", json_data=payload)

    if resp.status_code == 409:
        _log("FAIL", "Register from detect",
             "409 Duplicate — cleanup may have failed")
        return None

    if resp.status_code != 201:
        _log("FAIL", "Register from detect",
             f"HTTP {resp.status_code}: {resp.text[:300]}")
        return None

    agent = resp.json()
    checks = [
        agent.get("id"),
        agent.get("status") == "active",
        len(agent.get("skills", [])) > 0,
        agent.get("endpoint", "").startswith("https://e2e-register-test-"),
    ]
    if all(checks):
        _log("PASS", "Register from detect",
             f"id={agent['id'][:12]}... status=active, skills={len(agent['skills'])}")
    else:
        _log("FAIL", "Register from detect",
             f"Unexpected: {json.dumps(agent)[:300]}")

    return agent.get("id")


def test_duplicate_register_blocked(client: Client, registered_endpoint: str):
    """Second registration with same endpoint returns 409."""
    if not registered_endpoint:
        _log("SKIP", "Duplicate register", "No registered endpoint")
        return

    # Minimal payload with the same endpoint
    payload = {
        "name": "Duplicate Test",
        "description": "Should be rejected",
        "version": "1.0.0",
        "endpoint": registered_endpoint,
        "capabilities": {},
        "skills": [{
            "skill_key": "dup-test", "name": "Dup", "description": "test",
            "input_modes": ["text"], "output_modes": ["text"],
            "examples": [], "avg_credits": 0, "avg_latency_ms": 0,
        }],
        "security_schemes": [],
        "category": "testing",
        "tags": [],
        "pricing": {"license_type": "open", "model": "per_task", "credits": 1},
    }
    resp = client.post("/agents/", json_data=payload)

    if resp.status_code == 409:
        _log("PASS", "Duplicate register blocked", resp.json().get("detail", ""))
    else:
        _log("FAIL", "Duplicate register blocked",
             f"Expected 409, got {resp.status_code}")
        if resp.status_code == 201:
            agent_id = resp.json().get("id")
            if agent_id:
                client.delete(f"/agents/{agent_id}/permanent")


def test_registered_agent_has_card(client: Client, agent_id: str):
    """Verify registered agent exposes A2A agent card."""
    resp = client.get(f"/agents/{agent_id}/card")
    if resp.status_code != 200:
        _log("FAIL", "Agent card", f"HTTP {resp.status_code}")
        return

    card = resp.json()
    required = ["name", "skills", "url", "version"]
    missing = [k for k in required if k not in card]
    if missing:
        _log("FAIL", "Agent card", f"Missing: {missing}")
    else:
        _log("PASS", "Agent card", f"name={card['name']}, skills={len(card['skills'])}")


def test_registered_agent_in_listing(client: Client, agent_id: str):
    """Verify registered agent appears in agent listing."""
    resp = client.get("/agents/", params={"per_page": 100})
    if resp.status_code != 200:
        _log("FAIL", "Agent listing", f"HTTP {resp.status_code}")
        return

    agents = resp.json().get("agents", resp.json().get("items", []))
    found = any(a["id"] == agent_id for a in agents)
    if found:
        _log("PASS", "Agent in listing", f"Found {agent_id[:12]}...")
    else:
        _log("FAIL", "Agent in listing", f"Agent {agent_id[:12]}... not in listing")


def test_cleanup_agent(client: Client, agent_id: str):
    """Permanently delete the test agent."""
    resp = client.delete(f"/agents/{agent_id}/permanent")
    if resp.status_code in (200, 204):
        _log("PASS", "Cleanup agent", f"Deleted {agent_id[:12]}...")
    else:
        _log("FAIL", "Cleanup agent",
             f"HTTP {resp.status_code}: {resp.text[:200]}")



# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Register-agent E2E tests")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    print("\n  Register-Agent E2E Tests")
    print(f"  Target: {args.base_url}\n")

    client = Client(args.base_url, args.api_key)

    # Phase 1: Detect endpoint tests
    print("─── Phase 1: Detect ───")
    test_detect_summarizer(client)
    test_detect_translator(client)
    test_detect_invalid_url(client)
    test_detect_response_schema(client)

    # Phase 2: Register from detect (uses unique endpoint to avoid conflicts)
    print("\n─── Phase 2: Register ───")
    agent_id = test_register_from_detect(client, detect_trans)

    if agent_id:
        # Get the registered endpoint for duplicate test
        resp = client.get(f"/agents/{agent_id}")
        registered_endpoint = resp.json().get("endpoint", "") if resp.status_code == 200 else ""
        test_duplicate_register_blocked(client, registered_endpoint)
        test_registered_agent_has_card(client, agent_id)
        test_registered_agent_in_listing(client, agent_id)

        # Phase 3: Cleanup
        print("\n─── Phase 3: Cleanup ───")
        test_cleanup_agent(client, agent_id)
    else:
        _log("SKIP", "Duplicate register", "No agent registered")
        _log("SKIP", "Agent card", "No agent registered")
        _log("SKIP", "Agent listing", "No agent registered")
        _log("SKIP", "Cleanup agent", "No agent registered")

    # Summary
    passed = sum(1 for r in _results if r["status"] == "PASS")
    failed = sum(1 for r in _results if r["status"] == "FAIL")
    skipped = sum(1 for r in _results if r["status"] == "SKIP")
    total = len(_results)
    print(f"\n  Results: {passed}/{total} passed, {failed} failed, {skipped} skipped")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
