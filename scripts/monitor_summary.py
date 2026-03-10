#!/usr/bin/env python3
"""Generate GitHub Actions step summary from monitor output."""

import json
import sys

data = json.load(open(sys.argv[1]))

total = data["total"]
healthy = data["healthy"]
unhealthy = data["unhealthy"]

status_emoji = "✅" if unhealthy == 0 else "🔴" if unhealthy > 2 else "🟡"

print(f"{status_emoji} **{healthy}/{total}** spaces healthy")
if unhealthy:
    print(f"  — **{unhealthy}** need attention")
print()

# Markdown table
print("| Space | Stage | HTTP | Response | Status |")
print("|-------|-------|------|----------|--------|")
for s in data["spaces"]:
    icon = "✅" if s["healthy"] else "❌"
    stage = (s.get("runtime_stage") or "?")[:20]
    http = s.get("http_status") or s.get("error") or "?"
    ms = f"{s['response_time_ms']}ms" if s.get("response_time_ms") else "—"
    slow = " ⚠️" if s.get("response_time_ms") and s["response_time_ms"] > 5000 else ""
    action = s.get("recovery_action", "")
    status = "healthy" if s["healthy"] else action
    print(f"| {icon} {s['space_name']} | {stage} | {http} | {ms}{slow} | {status} |")
