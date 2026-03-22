#!/usr/bin/env python3
"""Deploy the CrewHub Multi-Channel Gateway to HuggingFace Spaces.

Usage:
    python scripts/deploy_gateway.py [--space arimatch1/crewhub-gateway]
    python scripts/deploy_gateway.py --dry-run

Requires:
    - HF_TOKEN env var (or --token)
    - CREWHUB_API_URL, GATEWAY_SERVICE_KEY, GATEWAY_PUBLIC_URL env vars
      (required unless --dry-run; set as HF Space secrets)
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from huggingface_hub import HfApi
except ImportError:
    print("Install huggingface_hub: pip install huggingface_hub")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPACE = "arimatch1/crewhub-gateway"

# Secrets to set on the HF Space (values read from env vars of the same name)
GATEWAY_SECRETS = [
    "CREWHUB_API_URL",
    "GATEWAY_SERVICE_KEY",
    "GATEWAY_PUBLIC_URL",
]


def deploy_gateway(space_id: str, api: HfApi, secrets: dict, dry_run: bool = False):
    gateway_dir = REPO_ROOT / "demo_agents" / "gateway"
    if not gateway_dir.is_dir():
        print(f"ERROR: Gateway directory not found: {gateway_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Deploying gateway → {space_id}")
    print(f"Source: {gateway_dir}")
    print(f"{'='*60}")

    # List files to be uploaded
    print("Contents to upload:")
    for p in sorted(gateway_dir.rglob("*")):
        if p.is_file() and "__pycache__" not in str(p) and not p.name.endswith(".pyc"):
            print(f"  {p.relative_to(gateway_dir)}")

    if dry_run:
        print(f"\n[DRY RUN] Would upload {gateway_dir} to {space_id}")
        print("[DRY RUN] Would set secrets:", list(secrets.keys()))
        return

    # Create space if it doesn't exist
    try:
        api.repo_info(repo_id=space_id, repo_type="space")
        print(f"\nSpace {space_id} already exists.")
    except Exception:
        print(f"\nCreating space {space_id}...")
        api.create_repo(
            repo_id=space_id,
            repo_type="space",
            space_sdk="docker",
            private=False,
        )

    # Clean deploy: upload gateway dir, delete stale files, squash history
    print(f"Uploading to {space_id}...")
    api.upload_folder(
        folder_path=str(gateway_dir),
        repo_id=space_id,
        repo_type="space",
        ignore_patterns=["**/__pycache__/**", "*.pyc"],
        delete_patterns=["*"],
        commit_message="Deploy CrewHub Gateway from GitHub Actions",
    )
    print(f"Uploaded to {space_id}")

    api.super_squash_history(
        repo_id=space_id,
        repo_type="space",
        commit_message="Squashed: deploy CrewHub Gateway",
    )
    print("Squashed HF repo history")

    # Set secrets
    for key, value in secrets.items():
        api.add_space_secret(repo_id=space_id, key=key, value=value)
        print(f"Set secret: {key}")

    space_url = f"https://{space_id.replace('/', '-')}.hf.space"
    print(f"\nDone! Gateway will be live at {space_url}")


def main():
    parser = argparse.ArgumentParser(description="Deploy CrewHub Gateway to HF Spaces")
    parser.add_argument("--space", default=DEFAULT_SPACE, help="HF Space repo ID")
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"), help="HuggingFace token")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    args = parser.parse_args()

    if not args.token:
        print("ERROR: HF_TOKEN env var or --token required", file=sys.stderr)
        sys.exit(1)

    # Collect secret values from environment
    secrets = {}
    missing = []
    for key in GATEWAY_SECRETS:
        val = os.environ.get(key)
        if val:
            secrets[key] = val
        elif not args.dry_run:
            missing.append(key)

    if missing:
        print(f"ERROR: Missing required env vars for secrets: {', '.join(missing)}", file=sys.stderr)
        print("Set these env vars before deploying (they will be stored as HF Space secrets).")
        sys.exit(1)

    api = HfApi(token=args.token)
    deploy_gateway(args.space, api, secrets, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
