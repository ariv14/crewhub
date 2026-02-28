#!/usr/bin/env python3
"""Seed the CrewHub database with demo users, agents, and credits.

Usage:
    python scripts/seed.py                    # seed against http://localhost:8080
    python scripts/seed.py --url http://...   # seed against custom URL

Requires the backend to be running. Uses the REST API (not direct DB access)
so it works in both local and hosted deployments.
"""

from __future__ import annotations

import argparse
import sys

import httpx

BASE_URL = "http://localhost:8080"

DEMO_USER = {
    "email": "demo@crewhub.dev",
    "password": "DemoPass123!",
    "name": "Demo User",
}

ADMIN_USER = {
    "email": "admin@crewhub.dev",
    "password": "AdminPass123!",
    "name": "Admin",
}

CREDIT_AMOUNT = 1000.0


def _register_user(client: httpx.Client, user: dict) -> dict | None:
    """Register a user, return the JWT token dict or None."""
    resp = client.post(f"{BASE_URL}/api/v1/auth/register", json=user)
    if resp.status_code == 201:
        print(f"  [OK] Registered '{user['email']}'")
    elif resp.status_code == 409:
        print(f"  [SKIP] '{user['email']}' already exists")
    else:
        print(f"  [FAIL] Register '{user['email']}': {resp.status_code} - {resp.text[:200]}")
        return None

    # Login to get token (login reuses UserCreate schema, so name is required)
    resp = client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"], "name": user["name"]},
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"  [FAIL] Login '{user['email']}': {resp.status_code} - {resp.text[:200]}")
        return None


def _add_credits(client: httpx.Client, token: str, amount: float) -> bool:
    """Add credits via the purchase endpoint (requires DEBUG=true)."""
    resp = client.post(
        f"{BASE_URL}/api/v1/credits/purchase",
        json={"amount": amount},
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 201:
        print(f"  [OK] Added {amount} credits")
        return True
    else:
        print(f"  [WARN] Add credits: {resp.status_code} - {resp.text[:200]}")
        return False


def _promote_admin(client: httpx.Client, admin_email: str) -> bool:
    """Print instructions for promoting user to admin."""
    print(f"  [INFO] To promote '{admin_email}' to admin, run:")
    print(f"         sqlite3 crewhub.db \"UPDATE users SET is_admin=1 WHERE email='{admin_email}';\"")
    return True


def _register_agents(client: httpx.Client, token: str) -> int:
    """Register all 5 demo agents in the marketplace."""
    from demo_agents.run_all import AGENTS

    headers = {"Authorization": f"Bearer {token}"}
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
        resp = client.post(
            f"{BASE_URL}/api/v1/agents/",
            json=payload,
            headers=headers,
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

    return registered


def main():
    global BASE_URL

    parser = argparse.ArgumentParser(description="Seed CrewHub with demo data")
    parser.add_argument("--url", default=BASE_URL, help="Backend URL (default: http://localhost:8080)")
    args = parser.parse_args()
    BASE_URL = args.url.rstrip("/")

    print(f"\nSeeding CrewHub at {BASE_URL}\n")
    print("=" * 50)

    client = httpx.Client(timeout=10.0)

    # 1. Register demo user
    print("\n1. Creating demo user...")
    demo_token_data = _register_user(client, DEMO_USER)
    demo_token = demo_token_data.get("access_token") if demo_token_data else None

    # 2. Register admin user
    print("\n2. Creating admin user...")
    _register_user(client, ADMIN_USER)

    # 3. Add credits to demo user
    if demo_token:
        print(f"\n3. Adding {CREDIT_AMOUNT} credits to demo user...")
        _add_credits(client, demo_token, CREDIT_AMOUNT)
    else:
        print("\n3. Skipping credits (no demo token)")

    # 4. Promote admin
    print("\n4. Admin promotion...")
    _promote_admin(client, ADMIN_USER["email"])

    # 5. Register agents (using demo user's token)
    if demo_token:
        print("\n5. Registering demo agents in marketplace...")
        count = _register_agents(client, demo_token)
        print(f"\n   Registered {count}/5 agents")
    else:
        print("\n5. Skipping agent registration (no token)")

    # Summary
    print("\n" + "=" * 50)
    print("\nSeed complete! Demo credentials:")
    print(f"  Demo user:  {DEMO_USER['email']} / {DEMO_USER['password']}")
    print(f"  Admin user: {ADMIN_USER['email']} / {ADMIN_USER['password']}")
    print(f"  Credits:    {CREDIT_AMOUNT}")
    print()

    client.close()


if __name__ == "__main__":
    main()
