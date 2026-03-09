#!/usr/bin/env python3
"""Monitor HuggingFace Spaces and auto-recover failures.

Checks health of all agent spaces, auto-restarts crashed ones,
and factory-reboots spaces stuck in error state.

Usage:
    python scripts/monitor_spaces.py                # check all
    python scripts/monitor_spaces.py --dry-run      # report only
    python scripts/monitor_spaces.py --json         # JSON output (for CI)

Requires:
    - HF_TOKEN env var (write access to restart spaces)
    - pip install huggingface_hub httpx
"""

import argparse
import json
import os
import sys
import time

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

try:
    from huggingface_hub import HfApi
except ImportError:
    print("Install huggingface_hub: pip install huggingface_hub")
    sys.exit(1)

HF_NAMESPACE = "arimatch1"

# All monitored spaces: (space_suffix, health_endpoint)
SPACES = [
    # Agency divisions
    ("crewhub-agency-engineering", "/.well-known/agent-card.json"),
    ("crewhub-agency-design", "/.well-known/agent-card.json"),
    ("crewhub-agency-marketing", "/.well-known/agent-card.json"),
    ("crewhub-agency-product", "/.well-known/agent-card.json"),
    ("crewhub-agency-project-mgmt", "/.well-known/agent-card.json"),
    ("crewhub-agency-testing", "/.well-known/agent-card.json"),
    ("crewhub-agency-support", "/.well-known/agent-card.json"),
    ("crewhub-agency-spatial", "/.well-known/agent-card.json"),
    ("crewhub-agency-specialized", "/.well-known/agent-card.json"),
    # Core agents
    ("crewhub-agent-summarizer", "/.well-known/agent-card.json"),
    ("crewhub-agent-translator", "/.well-known/agent-card.json"),
    # Backend
    ("crewhub-staging", "/api/v1/agents/?per_page=1"),
]


def check_space_health(space_name: str, health_path: str, timeout: float = 15.0) -> dict:
    """Check if a space is healthy by hitting its health endpoint."""
    space_id = f"{HF_NAMESPACE}/{space_name}"
    url = f"https://{HF_NAMESPACE}-{space_name}.hf.space{health_path}"

    result = {
        "space_id": space_id,
        "space_name": space_name,
        "url": url,
        "healthy": False,
        "http_status": None,
        "runtime_stage": None,
        "error": None,
    }

    # Check HF runtime stage first
    try:
        api = HfApi()
        info = api.space_info(space_id)
        result["runtime_stage"] = info.runtime.stage if info.runtime else "unknown"
    except Exception as e:
        result["runtime_stage"] = f"api_error: {e}"

    # Check actual HTTP health
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        result["http_status"] = resp.status_code
        result["healthy"] = resp.status_code == 200
    except httpx.TimeoutException:
        result["error"] = "timeout"
    except httpx.ConnectError:
        result["error"] = "connection_refused"
    except Exception as e:
        result["error"] = str(e)

    return result


def recover_space(space_name: str, runtime_stage: str, dry_run: bool = False) -> str:
    """Attempt to recover an unhealthy space. Returns action taken."""
    space_id = f"{HF_NAMESPACE}/{space_name}"
    api = HfApi()

    # Backend space — don't auto-restart, just report
    if space_name in ("crewhub-staging", "crewhub"):
        return "skip (backend — manual restart required)"

    stage = runtime_stage.lower() if runtime_stage else ""

    if "build" in stage or "error" in stage or stage == "runtime_error":
        action = "factory_reboot"
        if not dry_run:
            try:
                api.restart_space(space_id, factory_reboot=True)
            except Exception:
                # Factory reboot failed, try variable trigger
                try:
                    api.add_space_variable(
                        space_id,
                        key="REBUILD_TRIGGER",
                        value=str(int(time.time())),
                    )
                    action = "rebuild_via_variable"
                except Exception as e:
                    return f"failed: {e}"
    elif stage in ("sleeping", "paused"):
        action = "wake_up (http ping)"
        # The health check itself wakes sleeping spaces
    else:
        action = "restart"
        if not dry_run:
            try:
                api.restart_space(space_id)
            except Exception:
                try:
                    api.restart_space(space_id, factory_reboot=True)
                    action = "factory_reboot (restart failed)"
                except Exception as e:
                    return f"failed: {e}"

    return f"{'[DRY RUN] ' if dry_run else ''}{action}"


def main():
    parser = argparse.ArgumentParser(description="Monitor HF Spaces health")
    parser.add_argument("--dry-run", action="store_true", help="Report only, don't recover")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    results = []
    unhealthy = []

    for space_name, health_path in SPACES:
        result = check_space_health(space_name, health_path)
        results.append(result)

        if not result["healthy"]:
            action = recover_space(space_name, result["runtime_stage"], dry_run=args.dry_run)
            result["recovery_action"] = action
            unhealthy.append(result)

    if args.json:
        output = {
            "total": len(results),
            "healthy": len(results) - len(unhealthy),
            "unhealthy": len(unhealthy),
            "spaces": results,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n{'Space':<40} {'Stage':<15} {'HTTP':<6} {'Status'}")
        print("─" * 85)
        for r in results:
            stage = (r["runtime_stage"] or "?")[:14]
            http = str(r["http_status"] or r.get("error", "?"))[:5]
            status = "✓ healthy" if r["healthy"] else f"✗ {r.get('recovery_action', 'unhealthy')}"
            print(f"{r['space_name']:<40} {stage:<15} {http:<6} {status}")

        print(f"\nTotal: {len(results)} | Healthy: {len(results) - len(unhealthy)} | Recovered: {len(unhealthy)}")

    # Exit with error code if any space is unhealthy (for CI)
    if unhealthy:
        sys.exit(1)


if __name__ == "__main__":
    main()
