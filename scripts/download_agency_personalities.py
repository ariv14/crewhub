#!/usr/bin/env python3
"""Download personality .md files from msitarzewski/agency-agents GitHub repo.

Usage:
    python scripts/download_agency_personalities.py
    python scripts/download_agency_personalities.py --divisions engineering design

Fetches markdown personality definitions via GitHub API (or `gh` CLI),
parses YAML frontmatter, and saves to demo_agents/agency/personalities/{division}/.
Also generates a manifest.json with parsed metadata for all personalities.
"""

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

REPO = "msitarzewski/agency-agents"
REPO_ROOT = Path(__file__).resolve().parent.parent
PERSONALITIES_DIR = REPO_ROOT / "demo_agents" / "agency" / "personalities"

DIVISIONS = [
    "design",
    "engineering",
    "marketing",
    "product",
    "project-management",
    "spatial-computing",
    "specialized",
    "support",
    "testing",
]


def _gh_api(path: str) -> dict | list:
    """Call GitHub API via gh CLI."""
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/contents/{path}"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Returns (metadata_dict, body_text).
    """
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()

    return meta, parts[2].strip()


def _derive_skill_id(filename: str, division: str) -> str:
    """Derive skill_id from filename by stripping division prefix and .md extension.

    e.g. engineering-frontend-developer.md → frontend-developer
         macos-spatial-metal-engineer.md → macos-spatial-metal-engineer (no division prefix)
    """
    stem = filename.removesuffix(".md")
    prefix = division + "-"
    if stem.startswith(prefix):
        return stem[len(prefix):]
    # Some files don't follow the {division}-{name} pattern
    return stem


def download_division(division: str) -> list[dict]:
    """Download all personality files for a division. Returns metadata list."""
    div_dir = PERSONALITIES_DIR / division
    div_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n--- {division} ---")
    entries = _gh_api(division)

    personalities = []
    for entry in entries:
        name = entry["name"]
        if not name.endswith(".md"):
            continue

        # Fetch file content
        file_data = _gh_api(f"{division}/{name}")
        content = base64.b64decode(file_data["content"]).decode("utf-8")

        # Save raw file
        (div_dir / name).write_text(content, encoding="utf-8")

        # Parse metadata
        meta, body = _parse_frontmatter(content)
        skill_id = _derive_skill_id(name, division)

        personality = {
            "filename": name,
            "division": division,
            "skill_id": skill_id,
            "name": meta.get("name", skill_id.replace("-", " ").title()),
            "description": meta.get("description", ""),
        }
        personalities.append(personality)
        print(f"  ✓ {name} → skill_id={skill_id}")

    return personalities


def main():
    parser = argparse.ArgumentParser(description="Download agency personality files")
    parser.add_argument("--divisions", nargs="+", default=DIVISIONS,
                        choices=DIVISIONS, help="Divisions to download")
    args = parser.parse_args()

    PERSONALITIES_DIR.mkdir(parents=True, exist_ok=True)

    all_personalities = []
    for division in args.divisions:
        personalities = download_division(division)
        all_personalities.extend(personalities)

    # Write manifest
    manifest = {
        "source": f"https://github.com/{REPO}",
        "divisions": {},
    }
    for div in args.divisions:
        div_personalities = [p for p in all_personalities if p["division"] == div]
        manifest["divisions"][div] = div_personalities

    manifest_path = PERSONALITIES_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\n✓ Downloaded {len(all_personalities)} personalities across {len(args.divisions)} divisions")
    print(f"  Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
