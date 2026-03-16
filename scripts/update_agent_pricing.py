#!/usr/bin/env python3
"""One-time script to update agent pricing on production/staging.

Run on the server (HF Space) or locally with DATABASE_URL set:
    python scripts/update_agent_pricing.py

Pricing strategy:
- Universal Translator: 5 credits (simple, low-cost intro agent)
- AI Agency agents: 15 credits (multi-skill, LLM-powered)
- Promptfoo: 10 credits (specialized eval tool)
- Default for unknown agents: 10 credits
"""

import asyncio
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


PRICING_MAP = {
    # Production agent IDs
    "2cbe6ba7-4961-42f3-9947-cb8d22d71c88": 5,     # Universal Translator
    "36cd3426-7a2c-47de-9e0e-463be6661567": 10,    # Promptfoo
    "66b7e81a-4b53-484d-bfac-f0e9284f654b": 15,    # AI Agency: Testing
    "9329334a-2e89-4021-8d59-07880f912518": 15,    # AI Agency: Support
    "620a1745-7113-4a3e-bc1f-d542d27aa2b3": 15,    # AI Agency: Specialized
    "041cccc1-89e1-49b8-bca4-410fd4ddd30d": 15,    # AI Agency: Spatial Computing
    "f39be959-3f55-4d46-b388-9c3368a3bfd7": 15,    # AI Agency: Project Management
    "1d715e56-008b-438a-8047-9e34028c2915": 15,    # AI Agency: Product
    "424c15b0-9c9e-4cc4-a23a-36775f04a7b3": 15,    # AI Agency: Engineering
    "149dc80f-644f-4fea-868d-35e9d453759b": 15,    # AI Agency: Design
}


async def main():
    from sqlalchemy import text
    from src.database import engine

    async with engine.begin() as conn:
        # Get current pricing
        result = await conn.execute(text(
            "SELECT id, name, pricing FROM agents WHERE status = 'active'"
        ))
        agents = result.fetchall()

        print(f"Found {len(agents)} active agents\n")
        updated = 0

        for agent in agents:
            agent_id = str(agent[0])
            name = agent[1]
            pricing = agent[2] if isinstance(agent[2], dict) else json.loads(agent[2]) if agent[2] else {}
            old_credits = pricing.get("credits", 0)

            # Look up new price
            new_credits = PRICING_MAP.get(agent_id, 10)  # default 10

            if old_credits != new_credits:
                pricing["credits"] = new_credits
                pricing_json = json.dumps(pricing)

                await conn.execute(
                    text("UPDATE agents SET pricing = :pricing WHERE id = :id"),
                    {"pricing": pricing_json, "id": agent_id},
                )
                print(f"  UPDATED: {name}: {old_credits} -> {new_credits} credits")
                updated += 1
            else:
                print(f"  OK:      {name}: {old_credits} credits (no change)")

        print(f"\nDone. Updated {updated} agent(s).")


if __name__ == "__main__":
    asyncio.run(main())
