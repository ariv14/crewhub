#!/usr/bin/env python3
"""Register AI Agency division agents with the CrewHub marketplace.

Usage:
    python scripts/register_agency_agents.py --api-key <key>
    python scripts/register_agency_agents.py --api-key <key> --base-url https://arimatch1-crewhub-staging.hf.space
    python scripts/register_agency_agents.py --api-key <key> --divisions engineering design

Reads personality metadata from manifest.json and registers each division
as an agent with its personalities as skills.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "demo_agents" / "agency" / "personalities" / "manifest.json"

HF_NAMESPACE = "arimatch1"

# Maps division → HF Space ID (must match deploy script)
SPACE_IDS = {
    "engineering": f"{HF_NAMESPACE}/crewhub-agency-engineering",
    "design": f"{HF_NAMESPACE}/crewhub-agency-design",
    "marketing": f"{HF_NAMESPACE}/crewhub-agency-marketing",
    "product": f"{HF_NAMESPACE}/crewhub-agency-product",
    "project-management": f"{HF_NAMESPACE}/crewhub-agency-project-mgmt",
    "testing": f"{HF_NAMESPACE}/crewhub-agency-testing",
    "support": f"{HF_NAMESPACE}/crewhub-agency-support",
    "spatial-computing": f"{HF_NAMESPACE}/crewhub-agency-spatial",
    "specialized": f"{HF_NAMESPACE}/crewhub-agency-specialized",
}

DIVISION_META = {
    "engineering": ("AI Agency: Engineering", "Software engineering experts — backend, frontend, DevOps, AI, mobile, prototyping", "development"),
    "design": ("AI Agency: Design", "Design specialists — UI, UX, brand, visual storytelling, creative direction", "design"),
    "marketing": ("AI Agency: Marketing", "Marketing experts — content, social media, growth, app store optimization", "marketing"),
    "product": ("AI Agency: Product", "Product management — feedback synthesis, sprint prioritization, trend research", "business"),
    "project-management": ("AI Agency: Project Management", "Project management — scheduling, operations, production, experiment tracking", "business"),
    "testing": ("AI Agency: Testing", "QA and testing — API testing, performance, evidence collection, workflow optimization", "development"),
    "support": ("AI Agency: Support", "Support operations — analytics, finance, infrastructure, legal compliance", "business"),
    "spatial-computing": ("AI Agency: Spatial Computing", "XR/spatial computing — visionOS, Metal, immersive experiences", "development"),
    "specialized": ("AI Agency: Specialized", "Specialized agents — data analytics, orchestration, identity/trust, reporting", "data"),
}


def register_division(division: str, personalities: list[dict], base_url: str, headers: dict) -> bool:
    """Register a single division agent with the marketplace."""
    space_id = SPACE_IDS[division]
    space_url = f"https://{space_id.replace('/', '-')}.hf.space"
    name, description, category = DIVISION_META[division]

    skills = []
    for p in personalities:
        skills.append({
            "skill_key": p["skill_id"],
            "name": p["name"],
            "description": p["description"],
            "input_modes": ["text"],
            "output_modes": ["text"],
        })

    payload = {
        "name": name,
        "description": description,
        "version": "1.0.0",
        "endpoint": space_url,
        "capabilities": {"streaming": False, "pushNotifications": False},
        "skills": skills,
        "security_schemes": [],
        "category": category,
        "tags": ["agency", division, "ai-team"],
        "pricing": {"model": "per_task", "credits": 2},
    }

    try:
        resp = httpx.post(
            f"{base_url}/api/v1/agents/",
            json=payload,
            headers=headers,
            timeout=15.0,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            print(f"  [OK] Registered '{name}' (id={data.get('id', 'N/A')}, skills={len(skills)})")
            return True
        elif resp.status_code == 409:
            print(f"  [SKIP] '{name}' already registered")
            return True
        else:
            print(f"  [FAIL] '{name}': {resp.status_code} - {resp.text[:200]}")
            return False
    except httpx.HTTPError as exc:
        print(f"  [FAIL] '{name}': {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Register agency agents with CrewHub marketplace")
    parser.add_argument("--api-key", required=True, help="API key or Bearer token")
    parser.add_argument("--base-url", default="http://localhost:8000",
                        help="Marketplace API base URL")
    parser.add_argument("--divisions", nargs="+", choices=list(SPACE_IDS.keys()),
                        help="Specific divisions to register (default: all in manifest)")
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found at {MANIFEST_PATH}")
        print("Run scripts/download_agency_personalities.py first.")
        sys.exit(1)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    divisions_data = manifest["divisions"]

    target_divisions = args.divisions or list(divisions_data.keys())

    # Auth header — API keys use X-API-Key, others use Bearer
    headers = {"Content-Type": "application/json"}
    if args.api_key.startswith("a2a_"):
        headers["X-API-Key"] = args.api_key
    else:
        headers["Authorization"] = f"Bearer {args.api_key}"

    registered = 0
    for division in target_divisions:
        if division not in divisions_data:
            print(f"  [SKIP] '{division}' not in manifest")
            continue
        if register_division(division, divisions_data[division], args.base_url, headers):
            registered += 1

    print(f"\nRegistered {registered}/{len(target_divisions)} agency divisions.")


if __name__ == "__main__":
    main()
