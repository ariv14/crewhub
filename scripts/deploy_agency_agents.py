#!/usr/bin/env python3
"""Deploy AI Agency division agents to HuggingFace Spaces.

Usage:
    python scripts/deploy_agency_agents.py --divisions engineering design
    python scripts/deploy_agency_agents.py --all
    python scripts/deploy_agency_agents.py --all --dry-run

Requires:
    - HF_TOKEN env var (or --token)
    - GROQ_API_KEY env var (or --groq-key)
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

try:
    from huggingface_hub import HfApi
except ImportError:
    print("Install huggingface_hub: pip install huggingface_hub")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
HF_NAMESPACE = "arimatch1"

AGENCY_CONFIGS = {
    "engineering": {
        "space_id": f"{HF_NAMESPACE}/crewhub-agency-engineering",
        "emoji": "⚙️",
        "title": "Engineering Division",
        "description": "Software engineering experts: backend, frontend, DevOps, AI, mobile, and prototyping",
    },
    "design": {
        "space_id": f"{HF_NAMESPACE}/crewhub-agency-design",
        "emoji": "🎨",
        "title": "Design Division",
        "description": "Design specialists: UI, UX, brand, visual storytelling, and creative direction",
    },
    "marketing": {
        "space_id": f"{HF_NAMESPACE}/crewhub-agency-marketing",
        "emoji": "📢",
        "title": "Marketing Division",
        "description": "Marketing experts: content, social media, growth, app store optimization",
    },
    "product": {
        "space_id": f"{HF_NAMESPACE}/crewhub-agency-product",
        "emoji": "📦",
        "title": "Product Division",
        "description": "Product management: feedback synthesis, sprint prioritization, trend research",
    },
    "project-management": {
        "space_id": f"{HF_NAMESPACE}/crewhub-agency-project-mgmt",
        "emoji": "📋",
        "title": "Project Management Division",
        "description": "Project management: scheduling, operations, production, experiment tracking",
    },
    "testing": {
        "space_id": f"{HF_NAMESPACE}/crewhub-agency-testing",
        "emoji": "🧪",
        "title": "Testing Division",
        "description": "QA and testing: API testing, performance, evidence collection, workflow optimization",
    },
    "support": {
        "space_id": f"{HF_NAMESPACE}/crewhub-agency-support",
        "emoji": "🛟",
        "title": "Support Division",
        "description": "Support operations: analytics, finance, infrastructure, legal compliance",
    },
    "spatial-computing": {
        "space_id": f"{HF_NAMESPACE}/crewhub-agency-spatial",
        "emoji": "🥽",
        "title": "Spatial Computing Division",
        "description": "XR/spatial computing: visionOS, Metal, immersive experiences, cockpit interaction",
    },
    "specialized": {
        "space_id": f"{HF_NAMESPACE}/crewhub-agency-specialized",
        "emoji": "🔬",
        "title": "Specialized Division",
        "description": "Specialized agents: data analytics, orchestration, identity/trust, reporting",
    },
}

ALL_DIVISIONS = list(AGENCY_CONFIGS.keys())


def _generate_readme(config: dict) -> str:
    """Generate README.md from template with division metadata."""
    template_path = REPO_ROOT / "demo_agents" / "agency" / "README.md.template"
    template = template_path.read_text(encoding="utf-8")
    return template.format(
        division_title=config["title"],
        emoji=config["emoji"],
        description=config["description"],
    )


def _prepare_upload_dir(division: str, config: dict) -> Path:
    """Create a temp directory with the right structure for HF upload.

    Only copies the personalities for the target division (not all 56 files).
    """
    tmp = Path(tempfile.mkdtemp(prefix=f"crewhub-agency-{division}-"))

    agency_src = REPO_ROOT / "demo_agents" / "agency"

    # Root files
    shutil.copy2(agency_src / "Dockerfile", tmp / "Dockerfile")
    (tmp / "README.md").write_text(_generate_readme(config), encoding="utf-8")

    # demo_agents package
    da = tmp / "demo_agents"
    da.mkdir()
    shutil.copy2(REPO_ROOT / "demo_agents" / "__init__.py", da / "__init__.py")
    shutil.copy2(REPO_ROOT / "demo_agents" / "base.py", da / "base.py")

    # demo_agents/agency package
    agency_dst = da / "agency"
    agency_dst.mkdir()
    shutil.copy2(agency_src / "__init__.py", agency_dst / "__init__.py")
    shutil.copy2(agency_src / "division_agent.py", agency_dst / "division_agent.py")
    shutil.copy2(agency_src / "personality_loader.py", agency_dst / "personality_loader.py")

    # Only copy this division's personalities
    src_personalities = agency_src / "personalities" / division
    dst_personalities = agency_dst / "personalities" / division
    if src_personalities.is_dir():
        shutil.copytree(src_personalities, dst_personalities)
    else:
        print(f"  WARNING: No personalities found at {src_personalities}")
        dst_personalities.mkdir(parents=True)

    return tmp


def deploy_division(division: str, config: dict, api: HfApi, groq_key: str, dry_run: bool = False):
    space_id = config["space_id"]
    space_url = f"https://{space_id.replace('/', '-')}.hf.space"

    print(f"\n{'='*60}")
    print(f"Deploying {division} → {space_id}")
    print(f"URL: {space_url}")
    print(f"{'='*60}")

    upload_dir = _prepare_upload_dir(division, config)
    print(f"Prepared upload dir: {upload_dir}")
    print("Contents:")
    for p in sorted(upload_dir.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(upload_dir)}")

    if dry_run:
        print("[DRY RUN] Skipping upload and secret setup")
        shutil.rmtree(upload_dir)
        return

    # Create space if it doesn't exist
    try:
        api.repo_info(repo_id=space_id, repo_type="space")
        print(f"Space {space_id} already exists.")
    except Exception:
        print(f"Creating space {space_id}...")
        api.create_repo(repo_id=space_id, repo_type="space", space_sdk="docker", private=False)

    # Upload (clean deploy: delete stale files, then squash history)
    api.upload_folder(
        folder_path=str(upload_dir),
        repo_id=space_id,
        repo_type="space",
        delete_patterns=["*"],
        commit_message=f"Deploy {division} division",
    )
    print(f"Uploaded to {space_id}")

    api.super_squash_history(
        repo_id=space_id,
        repo_type="space",
        commit_message=f"Squashed: deploy {division}",
    )
    print(f"Squashed history for {space_id}")

    # Set secrets — primary + fallback LLM provider keys
    secrets = {
        "MODEL": "groq/llama-3.3-70b-versatile",
        "GROQ_API_KEY": groq_key,
        "AGENT_URL": space_url,
        "DIVISION": division,
        "CREDITS_PER_TASK": "2",
    }
    # Add optional fallback provider keys (multi-provider resilience)
    for env_var in ("GEMINI_API_KEY", "CEREBRAS_API_KEY", "SAMBANOVA_API_KEY"):
        val = os.environ.get(env_var)
        if val:
            secrets[env_var] = val
    for key, value in secrets.items():
        api.add_space_secret(repo_id=space_id, key=key, value=value)
        print(f"Set secret: {key}")

    shutil.rmtree(upload_dir)
    print(f"Done! Agent will be live at {space_url}")


def main():
    parser = argparse.ArgumentParser(description="Deploy AI Agency agents to HF Spaces")
    parser.add_argument("--divisions", nargs="+", choices=ALL_DIVISIONS,
                        help="Specific divisions to deploy")
    parser.add_argument("--all", action="store_true", help="Deploy all divisions")
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"))
    parser.add_argument("--groq-key", default=os.environ.get("GROQ_API_KEY"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.all and not args.divisions:
        parser.error("Specify --divisions or --all")

    divisions = ALL_DIVISIONS if args.all else args.divisions

    if not args.token and not args.dry_run:
        print("ERROR: HF_TOKEN env var or --token required")
        sys.exit(1)
    if not args.groq_key and not args.dry_run:
        print("ERROR: GROQ_API_KEY env var or --groq-key required")
        sys.exit(1)

    api = HfApi(token=args.token) if args.token else None

    for division in divisions:
        config = AGENCY_CONFIGS[division]
        deploy_division(division, config, api, args.groq_key or "", dry_run=args.dry_run)

    print(f"\n✓ Deployed {len(divisions)} agency divisions!")
    print("\nAgent URLs:")
    for division in divisions:
        config = AGENCY_CONFIGS[division]
        space_url = f"https://{config['space_id'].replace('/', '-')}.hf.space"
        print(f"  {division}: {space_url}")
        print(f"    Agent card: {space_url}/.well-known/agent-card.json")


if __name__ == "__main__":
    main()
