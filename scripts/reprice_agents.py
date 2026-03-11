"""Reprice agents on staging to meaningful credit values.

Usage:
    python scripts/reprice_agents.py --api-key <key> [--base-url <url>] [--dry-run]

Pricing tiers:
    - Demo agents (Summarizer, Translator): 10 credits ($0.10)
    - Agency divisions (9 agents, 56 skills): 15 credits ($0.15)
    - E2E test agents: skip (test artifacts)
"""

import argparse
import json
import sys
import httpx

PRICING_RULES = [
    # (name_contains, new_credits, license_type)
    ("Universal Summarizer", 10, "commercial"),
    ("Universal Translator", 10, "commercial"),
    ("AI Agency:", 15, "commercial"),
]

DEFAULT_CREDITS = 10


def should_skip(name: str) -> bool:
    return "E2E" in name or "DevFlow Test" in name


def get_new_price(name: str) -> tuple[int, str]:
    for pattern, credits, license_type in PRICING_RULES:
        if pattern in name:
            return credits, license_type
    return DEFAULT_CREDITS, "commercial"


def main():
    parser = argparse.ArgumentParser(description="Reprice agents")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--base-url", default="https://arimatch1-crewhub-staging.hf.space")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    headers = {"X-API-Key": args.api_key}
    base = args.base_url.rstrip("/") + "/api/v1"

    # Fetch all agents
    resp = httpx.get(f"{base}/agents/?per_page=100", headers=headers, timeout=30)
    resp.raise_for_status()
    agents = resp.json().get("agents", resp.json())

    updated = 0
    skipped = 0

    for agent in agents:
        name = agent["name"]
        agent_id = agent["id"]
        current = agent.get("pricing", {})
        current_credits = current.get("credits", 0)

        if should_skip(name):
            print(f"  SKIP  {name} (test agent)")
            skipped += 1
            continue

        new_credits, new_license = get_new_price(name)

        if current_credits == new_credits and current.get("license_type") == new_license:
            print(f"  OK    {name} — already {new_credits} credits")
            continue

        print(f"  UPDATE {name}: {current_credits} → {new_credits} credits, license={new_license}")

        if not args.dry_run:
            new_pricing = {
                **current,
                "credits": new_credits,
                "license_type": new_license,
            }
            # Try owner update first, fall back to admin endpoint
            r = httpx.put(
                f"{base}/agents/{agent_id}",
                headers=headers,
                json={"pricing": new_pricing},
                timeout=30,
            )
            if r.status_code == 403:
                r = httpx.put(
                    f"{base}/admin/agents/{agent_id}/pricing",
                    headers=headers,
                    json={"pricing": new_pricing},
                    timeout=30,
                )
            if r.status_code == 200:
                updated += 1
            else:
                print(f"    ERROR {r.status_code}: {r.text[:200]}")

    print(f"\nDone: {updated} updated, {skipped} skipped")
    if args.dry_run:
        print("(dry run — no changes applied)")


if __name__ == "__main__":
    main()
