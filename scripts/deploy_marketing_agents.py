#!/usr/bin/env python3
"""Deploy Marketing AI agents to HuggingFace Spaces.

Usage:
    python scripts/deploy_marketing_agents.py --all
    python scripts/deploy_marketing_agents.py --divisions cro copywriter
    python scripts/deploy_marketing_agents.py --all --dry-run

Requires:
    - HF_TOKEN env var (or huggingface-cli login)
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

MARKETING_CONFIGS = {
    "cro": {
        "space_id": f"{HF_NAMESPACE}/crewhub-marketing-cro",
        "emoji": "📈",
        "title": "CRO Optimizer",
        "description": "Conversion rate optimization for landing pages, signup flows, and onboarding",
        "credits": "20",
    },
    "copywriter": {
        "space_id": f"{HF_NAMESPACE}/crewhub-marketing-copywriter",
        "emoji": "✍️",
        "title": "Marketing Copywriter",
        "description": "Conversion-focused copy for landing pages, emails, and ads using proven formulas",
        "credits": "20",
    },
    "seo": {
        "space_id": f"{HF_NAMESPACE}/crewhub-marketing-seo",
        "emoji": "🔍",
        "title": "SEO Auditor",
        "description": "Technical SEO audits, AI search optimization, and schema markup generation",
        "credits": "25",
    },
    "launch": {
        "space_id": f"{HF_NAMESPACE}/crewhub-marketing-launch",
        "emoji": "🚀",
        "title": "Launch Strategist",
        "description": "Product launch planning, go-to-market strategy, and creative marketing ideas",
        "credits": "25",
    },
    "email": {
        "space_id": f"{HF_NAMESPACE}/crewhub-marketing-email",
        "emoji": "📧",
        "title": "Email Campaign Builder",
        "description": "Cold outreach, drip sequences, onboarding flows, and re-engagement campaigns",
        "credits": "20",
    },
    "pricing": {
        "space_id": f"{HF_NAMESPACE}/crewhub-marketing-pricing",
        "emoji": "💰",
        "title": "Pricing Strategist",
        "description": "SaaS pricing strategy, tier design, and competitor comparison pages",
        "credits": "20",
    },
}

ALL_DIVISIONS = list(MARKETING_CONFIGS.keys())


README_TEMPLATE = """---
title: CrewHub Marketing — {title}
emoji: {emoji}
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
---

# CrewHub Marketing: {title}

{description}

**Part of the [CrewHub AI Agent Marketplace](https://crewhubai.com)**

Powered by [marketingskills](https://github.com/coreyhaines31/marketingskills) by Corey Haines (MIT licensed).
"""


def _prepare_upload_dir(division: str, config: dict) -> Path:
    """Create temp dir with the right structure for HF upload."""
    tmp = Path(tempfile.mkdtemp(prefix=f"crewhub-mktg-{division}-"))

    marketing_src = REPO_ROOT / "demo_agents" / "marketing"

    # Dockerfile
    shutil.copy2(marketing_src / "Dockerfile", tmp / "Dockerfile")

    # README
    (tmp / "README.md").write_text(
        README_TEMPLATE.format(**config), encoding="utf-8"
    )

    # demo_agents package
    da = tmp / "demo_agents"
    da.mkdir()
    shutil.copy2(REPO_ROOT / "demo_agents" / "__init__.py", da / "__init__.py")
    shutil.copy2(REPO_ROOT / "demo_agents" / "base.py", da / "base.py")

    # demo_agents/marketing package
    mktg_dst = da / "marketing"
    mktg_dst.mkdir()
    shutil.copy2(marketing_src / "__init__.py", mktg_dst / "__init__.py")
    shutil.copy2(marketing_src / "marketing_agent.py", mktg_dst / "marketing_agent.py")
    shutil.copy2(marketing_src / "division_loader.py", mktg_dst / "division_loader.py")

    # Only copy this division's markdown file
    divisions_dst = mktg_dst / "divisions"
    divisions_dst.mkdir()
    src_file = marketing_src / "divisions" / f"{division}.md"
    if src_file.exists():
        shutil.copy2(src_file, divisions_dst / f"{division}.md")
    else:
        print(f"  WARNING: Division file not found: {src_file}")

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
        print("[DRY RUN] Skipping upload")
        shutil.rmtree(upload_dir)
        return

    # Create space if needed
    try:
        api.repo_info(repo_id=space_id, repo_type="space")
        print(f"Space {space_id} already exists.")
    except Exception:
        print(f"Creating space {space_id}...")
        api.create_repo(repo_id=space_id, repo_type="space", space_sdk="docker", private=False)

    # Upload
    api.upload_folder(
        folder_path=str(upload_dir),
        repo_id=space_id,
        repo_type="space",
        delete_patterns=["*"],
        commit_message=f"Deploy marketing {division}",
    )
    print(f"Uploaded to {space_id}")

    api.super_squash_history(
        repo_id=space_id,
        repo_type="space",
        commit_message=f"Squashed: deploy marketing {division}",
    )

    # Set secrets
    secrets = {
        "MODEL": "groq/llama-3.3-70b-versatile",
        "GROQ_API_KEY": groq_key,
        "AGENT_URL": space_url,
        "DIVISION": division,
        "CREDITS_PER_TASK": config["credits"],
    }
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
    parser = argparse.ArgumentParser(description="Deploy Marketing agents to HF Spaces")
    parser.add_argument("--divisions", nargs="+", choices=ALL_DIVISIONS)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--groq-key", default=os.environ.get("GROQ_API_KEY"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.all and not args.divisions:
        parser.error("Specify --divisions or --all")

    divisions = ALL_DIVISIONS if args.all else args.divisions

    if not args.groq_key and not args.dry_run:
        print("ERROR: GROQ_API_KEY env var or --groq-key required")
        sys.exit(1)

    api = HfApi()
    print(f"Logged in as: {api.whoami()['name']}")
    print(f"Deploying {len(divisions)} marketing agent(s): {', '.join(divisions)}")

    for div in divisions:
        config = MARKETING_CONFIGS[div]
        deploy_division(div, config, api, args.groq_key or "", args.dry_run)

    print(f"\n{'='*60}")
    print(f"All {len(divisions)} marketing agents deployed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
