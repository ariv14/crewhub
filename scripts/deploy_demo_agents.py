#!/usr/bin/env python3
"""Deploy demo agents (Summarizer & Translator) to HuggingFace Spaces.

Usage:
    python scripts/deploy_demo_agents.py [--agents summarizer translator]
    python scripts/deploy_demo_agents.py --dry-run

Requires:
    - HF_TOKEN env var (or --token)
    - GROQ_API_KEY env var (or --groq-key) for setting Space secrets
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

AGENT_CONFIGS = {
    "summarizer": {
        "space_id": f"{HF_NAMESPACE}/crewhub-agent-summarizer",
        "module": "demo_agents.summarizer.agent:app",
        "agent_dir": "demo_agents/summarizer",
    },
    "translator": {
        "space_id": f"{HF_NAMESPACE}/crewhub-agent-translator",
        "module": "demo_agents.translator.agent:app",
        "agent_dir": "demo_agents/translator",
    },
}


def _prepare_upload_dir(agent_name: str, config: dict) -> Path:
    """Create a temp directory with the right structure for HF upload.

    HF Spaces builds from the repo root, so we need:
      Dockerfile          (from demo_agents/<agent>/Dockerfile)
      README.md           (from demo_agents/<agent>/README.md)
      demo_agents/__init__.py
      demo_agents/base.py
      demo_agents/<agent>/__init__.py
      demo_agents/<agent>/agent.py
    """
    tmp = Path(tempfile.mkdtemp(prefix=f"crewhub-{agent_name}-"))

    agent_dir = REPO_ROOT / config["agent_dir"]

    # Dockerfile and README at root
    shutil.copy2(agent_dir / "Dockerfile", tmp / "Dockerfile")
    shutil.copy2(agent_dir / "README.md", tmp / "README.md")

    # Module structure
    da = tmp / "demo_agents"
    da.mkdir()
    shutil.copy2(REPO_ROOT / "demo_agents" / "__init__.py", da / "__init__.py")
    shutil.copy2(REPO_ROOT / "demo_agents" / "base.py", da / "base.py")

    agent_mod = da / agent_name
    agent_mod.mkdir()
    shutil.copy2(agent_dir / "__init__.py", agent_mod / "__init__.py")
    shutil.copy2(agent_dir / "agent.py", agent_mod / "agent.py")

    return tmp


def deploy_agent(agent_name: str, config: dict, api: HfApi, groq_key: str, dry_run: bool = False):
    space_id = config["space_id"]
    space_url = f"https://{space_id.replace('/', '-')}.hf.space"

    print(f"\n{'='*60}")
    print(f"Deploying {agent_name} → {space_id}")
    print(f"URL: {space_url}")
    print(f"{'='*60}")

    upload_dir = _prepare_upload_dir(agent_name, config)
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
        commit_message=f"Deploy {agent_type} agent",
    )
    print(f"Uploaded to {space_id}")

    api.super_squash_history(
        repo_id=space_id,
        repo_type="space",
        commit_message=f"Squashed: deploy {agent_type}",
    )
    print(f"Squashed history for {space_id}")

    # Set secrets
    secrets = {
        "MODEL": "groq/llama-3.3-70b-versatile",
        "GROQ_API_KEY": groq_key,
        "AGENT_URL": space_url,
    }
    for key, value in secrets.items():
        api.add_space_secret(repo_id=space_id, key=key, value=value)
        print(f"Set secret: {key}")

    shutil.rmtree(upload_dir)
    print(f"Done! Agent will be live at {space_url}")


def main():
    parser = argparse.ArgumentParser(description="Deploy demo agents to HF Spaces")
    parser.add_argument("--agents", nargs="+", default=["summarizer", "translator"],
                        choices=list(AGENT_CONFIGS.keys()))
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"))
    parser.add_argument("--groq-key", default=os.environ.get("GROQ_API_KEY"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.token:
        print("ERROR: HF_TOKEN env var or --token required")
        sys.exit(1)
    if not args.groq_key and not args.dry_run:
        print("ERROR: GROQ_API_KEY env var or --groq-key required")
        sys.exit(1)

    api = HfApi(token=args.token)

    for agent_name in args.agents:
        config = AGENT_CONFIGS[agent_name]
        deploy_agent(agent_name, config, api, args.groq_key or "", dry_run=args.dry_run)

    print("\n✓ All agents deployed!")
    print("\nAgent URLs:")
    for agent_name in args.agents:
        config = AGENT_CONFIGS[agent_name]
        space_url = f"https://{config['space_id'].replace('/', '-')}.hf.space"
        print(f"  {agent_name}: {space_url}")
        print(f"    Agent card: {space_url}/.well-known/agent-card.json")


if __name__ == "__main__":
    main()
