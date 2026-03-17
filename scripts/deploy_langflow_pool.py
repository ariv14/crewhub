#!/usr/bin/env python3
"""Deploy Langflow pool Spaces to HuggingFace.

Usage:
    python scripts/deploy_langflow_pool.py --pool-size 3
    python scripts/deploy_langflow_pool.py --pool-size 3 --dry-run

Requires:
    - HF_TOKEN env var (or huggingface-cli login)
    - CREWHUB_POOL_TOKEN env var (API key for CrewHub Agent component)
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


def _generate_readme(pool_id: int) -> str:
    template_path = REPO_ROOT / "demo_agents" / "langflow" / "README.md.template"
    template = template_path.read_text(encoding="utf-8")
    return template.format(pool_name=f"Pool {pool_id:02d}", pool_id=pool_id)


def _prepare_upload_dir(pool_id: int) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix=f"crewhub-langflow-pool-{pool_id:02d}-"))
    langflow_src = REPO_ROOT / "demo_agents" / "langflow"

    shutil.copy2(langflow_src / "Dockerfile", tmp / "Dockerfile")
    (tmp / "README.md").write_text(_generate_readme(pool_id), encoding="utf-8")

    components_dst = tmp / "components"
    shutil.copytree(
        langflow_src / "components", components_dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    return tmp


def deploy_pool_space(pool_id: int, api: HfApi, dry_run: bool = False):
    space_id = f"{HF_NAMESPACE}/crewhub-langflow-pool-{pool_id:02d}"
    space_url = f"https://{HF_NAMESPACE}-crewhub-langflow-pool-{pool_id:02d}.hf.space"

    print(f"\n{'='*60}")
    print(f"Deploying pool Space {pool_id:02d} → {space_id}")
    print(f"URL: {space_url}")
    print(f"{'='*60}")

    upload_dir = _prepare_upload_dir(pool_id)
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
        api.create_repo(
            repo_id=space_id, repo_type="space",
            space_sdk="docker", private=False,
        )

    # Upload
    api.upload_folder(
        folder_path=str(upload_dir),
        repo_id=space_id,
        repo_type="space",
        delete_patterns=["*"],
        commit_message=f"Deploy langflow pool {pool_id:02d}",
    )
    api.super_squash_history(
        repo_id=space_id, repo_type="space",
        commit_message=f"Squashed: pool {pool_id:02d}",
    )
    print(f"Uploaded to {space_id}")

    # Set secrets
    secrets = {
        "LANGFLOW_LOGIN_ENABLED": "False",
        "LANGFLOW_AUTO_LOGIN": "True",
        "LANGFLOW_LOG_LEVEL": "INFO",
        "CREWHUB_API_URL": "https://api.crewhubai.com",
    }
    crewhub_token = os.environ.get("CREWHUB_POOL_TOKEN", "")
    if crewhub_token:
        secrets["CREWHUB_AGENT_TOKEN"] = crewhub_token

    for key, value in secrets.items():
        api.add_space_secret(repo_id=space_id, key=key, value=value)
        print(f"Set secret: {key}")

    shutil.rmtree(upload_dir)
    print(f"Done! Space at {space_url}")


def main():
    parser = argparse.ArgumentParser(description="Deploy Langflow pool Spaces")
    parser.add_argument("--pool-size", type=int, default=3, help="Number of pool Spaces")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api = HfApi()
    print(f"Logged in as: {api.whoami()['name']}")
    print(f"Deploying {args.pool_size} pool Space(s)")

    for i in range(1, args.pool_size + 1):
        deploy_pool_space(i, api, args.dry_run)

    print(f"\n{'='*60}")
    print(f"All {args.pool_size} pool Spaces deployed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
