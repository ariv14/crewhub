#!/usr/bin/env python3
"""Generate GitHub Actions step summary from monitor output."""

import json
import sys

data = json.load(open(sys.argv[1]))

print(f"- **Total**: {data['total']} spaces")
print(f"- **Healthy**: {data['healthy']}")
print(f"- **Unhealthy/Recovered**: {data['unhealthy']}")
print()
print("```")
for s in data["spaces"]:
    icon = "✓" if s["healthy"] else "✗"
    stage = (s.get("runtime_stage") or "?")[:14]
    http = s.get("http_status") or "?"
    action = s.get("recovery_action", "")
    print(f"{icon} {s['space_name']:<40} {stage:<15} HTTP {http:<4} {action}")
print("```")
