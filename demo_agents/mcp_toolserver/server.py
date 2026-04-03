# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Lightweight MCP tool server — provides real tools for demo/testing.

Implements JSON-RPC 2.0 transport for MCP tools/list and tools/call.
Each tool returns real, useful data.

Tools:
  - get_weather: Returns weather for a city (simulated realistic data)
  - get_crypto_prices: Returns current crypto prices (simulated)
  - get_tech_news: Returns trending tech headlines (simulated)
  - calculate: Evaluate a math expression safely using ast.literal_eval

Port: 7861
"""

import ast
import hashlib
import os
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="CrewHub MCP Tool Server")

TOOLS = [
    {
        "name": "get_weather",
        "description": "Get current weather for a city. Returns temperature, conditions, humidity, and wind.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name (e.g. 'Tokyo', 'London')"},
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_crypto_prices",
        "description": "Get current cryptocurrency prices. Returns top coins with price, 24h change, and market cap.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "coins": {
                    "type": "string",
                    "description": "Comma-separated coin symbols (e.g. 'BTC,ETH,SOL'). Default: top 5.",
                },
            },
        },
    },
    {
        "name": "get_tech_news",
        "description": "Get trending tech news headlines. Returns title, source, and summary for recent articles.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Filter by topic (e.g. 'AI', 'crypto', 'startups'). Default: all."},
                "limit": {"type": "integer", "description": "Number of headlines (1-10). Default: 5."},
            },
        },
    },
    {
        "name": "calculate",
        "description": "Evaluate a simple arithmetic expression. Supports +, -, *, /, ** (power). No variables or functions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Arithmetic expression (e.g. '2**10', '3.14 * 5**2', '100 / 3')"},
            },
            "required": ["expression"],
        },
    },
]


def _deterministic_float(seed: str, low: float, high: float) -> float:
    """Generate a deterministic float from a seed string, for realistic simulated data."""
    h = int(hashlib.md5(f"{seed}{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H')}".encode()).hexdigest()[:8], 16)
    return low + (h % 10000) / 10000 * (high - low)


def _handle_get_weather(args: dict) -> dict:
    city = args.get("city", "Unknown")
    seed = city.lower()
    temp = round(_deterministic_float(seed + "temp", -10, 38), 1)
    humidity = round(_deterministic_float(seed + "hum", 20, 95))
    wind = round(_deterministic_float(seed + "wind", 0, 40), 1)
    conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Stormy", "Snowy", "Foggy", "Clear"]
    cond_idx = int(_deterministic_float(seed + "cond", 0, len(conditions) - 0.01))
    return {
        "city": city,
        "temperature_celsius": temp,
        "conditions": conditions[cond_idx],
        "humidity_percent": humidity,
        "wind_kmh": wind,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _handle_get_crypto_prices(args: dict) -> dict:
    coins_str = args.get("coins", "BTC,ETH,SOL,ADA,DOT")
    coins = [c.strip().upper() for c in coins_str.split(",")]
    base_prices = {"BTC": 95000, "ETH": 4200, "SOL": 180, "ADA": 0.65, "DOT": 8.5, "AVAX": 42, "LINK": 18, "XRP": 2.1, "DOGE": 0.18, "MATIC": 0.95}
    results = []
    for coin in coins[:10]:
        base = base_prices.get(coin, 10.0)
        price = round(base * (1 + _deterministic_float(coin + "p", -0.05, 0.05)), 2)
        change = round(_deterministic_float(coin + "c", -8, 12), 2)
        mcap = f"${round(price * _deterministic_float(coin + 'm', 1e6, 1e9) / 1e9, 1)}B"
        results.append({"symbol": coin, "price_usd": price, "change_24h_percent": change, "market_cap": mcap})
    return {"prices": results, "updated_at": datetime.now(timezone.utc).isoformat()}


def _handle_get_tech_news(args: dict) -> dict:
    topic = args.get("topic", "").lower()
    limit = min(args.get("limit", 5), 10)
    all_news = [
        {"title": "OpenAI launches GPT-5 with native agent capabilities", "source": "TechCrunch", "topic": "ai", "summary": "New model supports autonomous tool use and multi-step planning out of the box."},
        {"title": "Google's Agent Protocol reaches 1M daily transactions", "source": "The Verge", "topic": "ai", "summary": "A2A protocol adoption accelerates as enterprises build agent-to-agent workflows."},
        {"title": "Bitcoin ETF inflows hit record $2.1B in single day", "source": "CoinDesk", "topic": "crypto", "summary": "Institutional demand surges as BTC approaches all-time highs."},
        {"title": "Anthropic raises $5B Series E at $120B valuation", "source": "Bloomberg", "topic": "ai", "summary": "Funding will accelerate enterprise AI safety research and Claude development."},
        {"title": "Y Combinator S26 batch features 40% AI-native startups", "source": "TechCrunch", "topic": "startups", "summary": "Agent marketplaces, AI dev tools, and vertical AI dominate latest cohort."},
        {"title": "EU AI Act enforcement begins: first compliance audits underway", "source": "Reuters", "topic": "ai", "summary": "High-risk AI systems face mandatory transparency and safety requirements."},
        {"title": "Solana processes 100K TPS in mainnet stress test", "source": "CoinDesk", "topic": "crypto", "summary": "Network upgrade enables parallel transaction execution at scale."},
        {"title": "GitHub Copilot agents can now create pull requests autonomously", "source": "GitHub Blog", "topic": "ai", "summary": "New agent mode handles multi-file changes with test generation and review."},
        {"title": "Stripe launches native agent payments with x402 protocol", "source": "Stripe Blog", "topic": "startups", "summary": "Agents can now pay for services programmatically using HTTP 402 flows."},
        {"title": "Apple announces visionOS 4 with spatial AI agent support", "source": "MacRumors", "topic": "ai", "summary": "Vision Pro gets native agent framework for spatial computing workflows."},
    ]
    if topic:
        filtered = [n for n in all_news if n["topic"] == topic]
    else:
        filtered = all_news
    return {"articles": filtered[:limit], "total": len(filtered)}


def _safe_calculate(expr: str) -> dict:
    """Safely evaluate arithmetic expressions using AST parsing — no code execution."""
    allowed = {ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
               ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd}
    try:
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if type(node) not in allowed:
                return {"expression": expr, "error": f"Unsupported operation: {type(node).__name__}. Only arithmetic (+,-,*,/,**) allowed."}
        code = compile(tree, "<calc>", "eval")
        result = eval(code, {"__builtins__": {}})  # noqa: S307 — AST-validated, only arithmetic ops
        return {"expression": expr, "result": result}
    except Exception as exc:
        return {"expression": expr, "error": str(exc)}


HANDLERS = {
    "get_weather": _handle_get_weather,
    "get_crypto_prices": _handle_get_crypto_prices,
    "get_tech_news": _handle_get_tech_news,
    "calculate": _safe_calculate,
}


@app.post("/")
async def jsonrpc_handler(request: Request):
    body = await request.json()
    method = body.get("method", "")
    params = body.get("params", {})
    req_id = body.get("id")

    if method == "tools/list":
        return JSONResponse(content={
            "jsonrpc": "2.0", "id": req_id,
            "result": {"tools": TOOLS},
        })

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        handler = HANDLERS.get(tool_name)
        if not handler:
            return JSONResponse(content={
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
            })
        result = handler(arguments)
        return JSONResponse(content={
            "jsonrpc": "2.0", "id": req_id,
            "result": {"content": [{"type": "text", "text": str(result)}], "data": result},
        })

    return JSONResponse(content={
        "jsonrpc": "2.0", "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    })


@app.get("/")
async def health():
    return {"status": "ok", "tools": len(TOOLS), "service": "CrewHub MCP Tool Server"}
