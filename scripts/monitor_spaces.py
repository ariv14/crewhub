#!/usr/bin/env python3
"""Monitor HuggingFace Spaces and auto-recover failures.

Checks health of all agent spaces concurrently, auto-restarts crashed ones,
factory-reboots spaces stuck in error state, and alerts via Discord.

Usage:
    python scripts/monitor_spaces.py                # check all
    python scripts/monitor_spaces.py --dry-run      # report only
    python scripts/monitor_spaces.py --json         # JSON output (for CI)

Requires:
    - HF_TOKEN env var (write access to restart spaces)
    - pip install huggingface_hub httpx

Optional:
    - DISCORD_HEALTHCHECK_WEBHOOK env var (Discord webhook URL for alerts)
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

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
MAX_WORKERS = 8
SLOW_THRESHOLD_MS = 5000  # flag responses slower than 5s

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
    # Promptfoo agent
    ("crewhub-agent-promptfoo", "/.well-known/agent-card.json"),
    # Marketing specialists
    ("crewhub-marketing-cro", "/.well-known/agent-card.json"),
    ("crewhub-marketing-copywriter", "/.well-known/agent-card.json"),
    ("crewhub-marketing-seo", "/.well-known/agent-card.json"),
    ("crewhub-marketing-launch", "/.well-known/agent-card.json"),
    ("crewhub-marketing-email", "/.well-known/agent-card.json"),
    ("crewhub-marketing-pricing", "/.well-known/agent-card.json"),
    # Backend
    ("crewhub-staging", "/api/v1/agents/?per_page=1"),
    ("crewhub", "/api/v1/agents/?per_page=1"),
]

# Shared HfApi instance
_hf_api = HfApi()


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
        "response_time_ms": None,
        "error": None,
    }

    # Check HF runtime stage
    try:
        info = _hf_api.space_info(space_id)
        result["runtime_stage"] = info.runtime.stage if info.runtime else "unknown"
    except Exception as e:
        result["runtime_stage"] = f"api_error: {e}"

    # Check actual HTTP health with response time
    try:
        start = time.monotonic()
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        elapsed_ms = round((time.monotonic() - start) * 1000)
        result["http_status"] = resp.status_code
        result["response_time_ms"] = elapsed_ms
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

    # Backend spaces — don't auto-restart, just report
    if space_name in ("crewhub-staging", "crewhub"):
        return "skip (backend — manual restart required)"

    stage = runtime_stage.lower() if runtime_stage else ""

    # NEVER use factory_reboot — it wipes Docker cache, causes 10+ min rebuilds
    if stage in ("sleeping", "paused"):
        action = "wake_up (http ping)"
        # The health check itself wakes sleeping spaces
    elif "error" in stage or "build" in stage or stage == "runtime_error":
        action = "soft_restart"
        if not dry_run:
            try:
                _hf_api.restart_space(space_id)
            except Exception as e:
                return f"failed: {e}"
    else:
        action = "soft_restart"
        if not dry_run:
            try:
                _hf_api.restart_space(space_id)
            except Exception as e:
                return f"failed: {e}"

    return f"{'[DRY RUN] ' if dry_run else ''}{action}"


def send_discord_alert(results: list[dict], unhealthy: list[dict]) -> None:
    """Send a Discord embed summarizing failures."""
    webhook_url = os.environ.get("DISCORD_HEALTHCHECK_WEBHOOK")
    if not webhook_url or not unhealthy:
        return

    total = len(results)
    healthy_count = total - len(unhealthy)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Build failure lines
    lines = []
    for r in unhealthy:
        stage = (r.get("runtime_stage") or "unknown")[:20]
        action = r.get("recovery_action", "none")
        error = r.get("error") or f"HTTP {r.get('http_status', '?')}"
        lines.append(f"**{r['space_name']}** — {error} (stage: {stage}, action: {action})")

    # Build slow space lines
    slow = [
        r for r in results
        if r["healthy"] and r.get("response_time_ms") and r["response_time_ms"] > SLOW_THRESHOLD_MS
    ]
    if slow:
        lines.append("")
        lines.append("**Slow but alive:**")
        for r in slow:
            lines.append(f"  {r['space_name']} — {r['response_time_ms']}ms")

    description = "\n".join(lines[:20])  # cap at 20 lines

    embed = {
        "title": f"Space Monitor: {len(unhealthy)} unhealthy / {total} total",
        "description": description,
        "color": 0xFF4444 if len(unhealthy) > 2 else 0xFFA500,  # red if many, orange if few
        "footer": {"text": f"{now} | {healthy_count}/{total} healthy"},
    }

    try:
        httpx.post(webhook_url, json={"embeds": [embed]}, timeout=10)
    except Exception as e:
        print(f"Discord alert failed: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Monitor HF Spaces health")
    parser.add_argument("--dry-run", action="store_true", help="Report only, don't recover")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    results = []
    unhealthy = []

    # Check all spaces concurrently
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_space = {
            executor.submit(check_space_health, name, path): (name, path)
            for name, path in SPACES
        }
        # Collect in submission order
        future_order = list(future_to_space.keys())
        for future in future_order:
            result = future.result()
            results.append(result)

            if not result["healthy"]:
                action = recover_space(result["space_name"], result["runtime_stage"], dry_run=args.dry_run)
                result["recovery_action"] = action
                unhealthy.append(result)

    # Discord alert for failures
    send_discord_alert(results, unhealthy)

    if args.json:
        output = {
            "total": len(results),
            "healthy": len(results) - len(unhealthy),
            "unhealthy": len(unhealthy),
            "spaces": results,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n{'Space':<40} {'Stage':<15} {'HTTP':<6} {'Time':<8} {'Status'}")
        print("─" * 95)
        for r in results:
            stage = (r["runtime_stage"] or "?")[:14]
            http = str(r["http_status"] or r.get("error", "?"))[:5]
            ms = f"{r['response_time_ms']}ms" if r.get("response_time_ms") else "—"
            slow_flag = " ⚠" if r.get("response_time_ms") and r["response_time_ms"] > SLOW_THRESHOLD_MS else ""
            status = "✓ healthy" if r["healthy"] else f"✗ {r.get('recovery_action', 'unhealthy')}"
            print(f"{r['space_name']:<40} {stage:<15} {http:<6} {ms:<8} {status}{slow_flag}")

        print(f"\nTotal: {len(results)} | Healthy: {len(results) - len(unhealthy)} | Unhealthy: {len(unhealthy)}")

    if unhealthy:
        sys.exit(1)


if __name__ == "__main__":
    main()
