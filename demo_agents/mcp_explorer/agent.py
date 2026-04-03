# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""MCP Explorer Agent — demonstrates MCP tool access in action.

This agent uses the MCP toolkit to discover and call tools from external
MCP servers that the user has granted access to. It showcases the full
MCP flow: tool discovery → LLM decides which tool to call → tool execution
→ rich A2UI output.

Skills:
  - explore-tools    Discover available MCP tools and their capabilities
  - use-tool         Ask a question — agent picks and calls the right MCP tool

Port: 8007
Credits: 5 per task
"""

from __future__ import annotations

import json
import re

from demo_agents.base import (
    Artifact,
    MessagePart,
    StreamChunk,
    TaskMessage,
    create_a2a_app,
    emit_table,
    emit_chart,
    get_mcp,
    llm_call,
    llm_call_streaming,
)

PORT = 8007
CREDITS = 5

SKILLS = [
    {
        "id": "explore-tools",
        "name": "Explore MCP Tools",
        "description": (
            "Discover what tools are available from connected MCP servers. "
            "Shows tool names, descriptions, and parameters in a structured table."
        ),
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {"input": "What tools are available?", "output": "A table of all MCP tools with descriptions.", "description": "List tools"},
        ],
    },
    {
        "id": "use-tool",
        "name": "Use MCP Tool",
        "description": (
            "Ask any question — the agent will pick the right MCP tool, call it, "
            "and present the results as rich tables and charts. "
            "Try: 'What's the weather in Tokyo?', 'Show me crypto prices', 'Latest AI news'"
        ),
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {"input": "What's the weather in Tokyo?", "output": "Weather data from the MCP weather tool.", "description": "Weather query"},
            {"input": "Show me crypto prices for BTC, ETH, SOL", "output": "Price table with 24h change.", "description": "Crypto prices"},
            {"input": "Latest AI news", "output": "Tech news headlines table.", "description": "News query"},
        ],
    },
]


def _extract_json(text: str) -> dict | None:
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


TOOL_PICKER_PROMPT = """You are an AI assistant with access to external tools via MCP (Model Context Protocol).

Available tools:
{tools_json}

Based on the user's message, decide which tool to call. Return ONLY valid JSON:
{{
  "tool_name": "the_tool_name",
  "arguments": {{"arg1": "value1"}},
  "reasoning": "Brief explanation of why this tool was chosen"
}}

If no tool matches, return:
{{"tool_name": "none", "arguments": {{}}, "reasoning": "No suitable tool found"}}

IMPORTANT: Return ONLY the JSON, no other text."""


async def handle(skill_id: str, messages: list[TaskMessage]) -> list[Artifact]:
    text = ""
    for msg in messages:
        for part in msg.parts:
            if part.type == "text" and part.content:
                text += part.content + "\n"
    text = text.strip()

    if not text:
        return [Artifact(name="error", parts=[MessagePart(type="text", content="No input provided.")])]

    mcp = get_mcp()

    if not mcp or not mcp.server_names:
        return [Artifact(
            name="no-mcp-access",
            parts=[MessagePart(type="text", content=(
                "No MCP servers are connected to this agent. "
                "To use MCP tools, go to Dashboard → MCP Servers, register a server, "
                "and grant this agent access."
            ))],
        )]

    if skill_id == "explore-tools":
        return await _explore_tools(mcp)
    else:
        return await _use_tool(mcp, text)


async def _explore_tools(mcp) -> list[Artifact]:
    """List all tools from all connected MCP servers."""
    all_tools = []
    for server_name in mcp.server_names:
        tools = await mcp.list_tools(server_name)
        for t in tools:
            params = t.get("inputSchema", {}).get("properties", {})
            param_names = ", ".join(params.keys()) if params else "none"
            all_tools.append([server_name, t.get("name", ""), t.get("description", "")[:80], param_names])

    if not all_tools:
        return [Artifact(name="no-tools", parts=[MessagePart(type="text", content="Connected MCP servers have no tools available.")])]

    return [Artifact(
        name="mcp-tools",
        parts=[MessagePart(type="text", content=f"Found {len(all_tools)} tools across {len(mcp.server_names)} MCP server(s).")],
        ui_components=[
            emit_table("Available MCP Tools", ["Server", "Tool", "Description", "Parameters"], all_tools),
        ],
    )]


async def _use_tool(mcp, user_message: str) -> list[Artifact]:
    """Pick the right tool, call it, and present results."""
    # Gather all available tools
    all_tools = []
    tool_server_map = {}
    for server_name in mcp.server_names:
        tools = await mcp.list_tools(server_name)
        for t in tools:
            all_tools.append(t)
            tool_server_map[t["name"]] = server_name

    if not all_tools:
        return [Artifact(name="no-tools", parts=[MessagePart(type="text", content="No MCP tools available.")])]

    # Ask LLM which tool to call
    tools_json = json.dumps([{"name": t["name"], "description": t.get("description", ""), "parameters": t.get("inputSchema", {}).get("properties", {})} for t in all_tools], indent=2)
    prompt = TOOL_PICKER_PROMPT.format(tools_json=tools_json)
    decision_raw = await llm_call(prompt, user_message)
    decision = _extract_json(decision_raw)

    if not decision or decision.get("tool_name") == "none":
        return [Artifact(name="no-match", parts=[MessagePart(type="text", content=f"I couldn't find a suitable tool for your request. Available tools: {', '.join(t['name'] for t in all_tools)}")])]

    tool_name = decision["tool_name"]
    arguments = decision.get("arguments", {})
    reasoning = decision.get("reasoning", "")
    server_name = tool_server_map.get(tool_name)

    if not server_name:
        return [Artifact(name="error", parts=[MessagePart(type="text", content=f"Tool '{tool_name}' not found on any connected server.")])]

    # Call the tool
    result = await mcp.call_tool(server_name, tool_name, arguments)

    if isinstance(result, dict) and result.get("error"):
        return [Artifact(name="tool-error", parts=[MessagePart(type="text", content=f"Tool error: {result['error']}")])]

    # Extract data from result
    tool_data = result.get("data", result) if isinstance(result, dict) else result

    # Build rich output based on tool type
    components = []
    summary = f"Called **{tool_name}** on `{server_name}`"
    if reasoning:
        summary += f"\n\n*{reasoning}*"

    if tool_name == "get_weather" and isinstance(tool_data, dict):
        city = tool_data.get("city", "")
        components.append(emit_table(
            f"Weather in {city}",
            ["Metric", "Value"],
            [
                ["Temperature", f"{tool_data.get('temperature_celsius', '?')}°C"],
                ["Conditions", str(tool_data.get("conditions", "?"))],
                ["Humidity", f"{tool_data.get('humidity_percent', '?')}%"],
                ["Wind", f"{tool_data.get('wind_kmh', '?')} km/h"],
                ["Updated", str(tool_data.get("updated_at", "?"))[:19]],
            ],
        ))

    elif tool_name == "get_crypto_prices" and isinstance(tool_data, dict):
        prices = tool_data.get("prices", [])
        if prices:
            rows = [[p["symbol"], f"${p['price_usd']:,.2f}", f"{p['change_24h_percent']:+.2f}%", p.get("market_cap", "")] for p in prices]
            components.append(emit_table("Cryptocurrency Prices", ["Coin", "Price (USD)", "24h Change", "Market Cap"], rows))
            components.append(emit_chart(
                "Price Comparison",
                "bar",
                [p["symbol"] for p in prices],
                [{"label": "Price (USD)", "values": [p["price_usd"] for p in prices]}],
            ))

    elif tool_name == "get_tech_news" and isinstance(tool_data, dict):
        articles = tool_data.get("articles", [])
        if articles:
            rows = [[a["title"], a.get("source", ""), a.get("topic", ""), a.get("summary", "")[:60]] for a in articles]
            components.append(emit_table("Tech News", ["Title", "Source", "Topic", "Summary"], rows))

    elif tool_name == "calculate" and isinstance(tool_data, dict):
        expr = tool_data.get("expression", "")
        res = tool_data.get("result", tool_data.get("error", "?"))
        components.append(emit_table("Calculation Result", ["Expression", "Result"], [[expr, str(res)]]))

    else:
        # Generic: show raw result as table
        if isinstance(tool_data, dict):
            rows = [[k, str(v)[:100]] for k, v in tool_data.items()]
            components.append(emit_table(f"{tool_name} Result", ["Field", "Value"], rows))

    return [Artifact(
        name=f"mcp-{tool_name}",
        parts=[MessagePart(type="text", content=summary)],
        metadata={"tool": tool_name, "server": server_name, "arguments": arguments},
        ui_components=components,
    )]


async def handle_streaming(skill_id: str, messages: list[TaskMessage]):
    """Streaming version — shows progress as it discovers and calls tools."""
    text = ""
    for msg in messages:
        for part in msg.parts:
            if part.type == "text" and part.content:
                text += part.content + "\n"
    text = text.strip()

    mcp = get_mcp()

    if not mcp or not mcp.server_names:
        yield StreamChunk(type="error", content=(
            "No MCP servers connected. Go to Dashboard → MCP Servers to register "
            "a server and grant this agent access."
        ))
        return

    if skill_id == "explore-tools":
        yield StreamChunk(type="thinking", content="Discovering tools from connected MCP servers...")
        artifacts = await _explore_tools(mcp)
        yield StreamChunk(type="done", artifacts=artifacts)
        return

    # use-tool skill: show step-by-step progress
    yield StreamChunk(type="thinking", content="Discovering available tools...")

    all_tools = []
    tool_server_map = {}
    for server_name in mcp.server_names:
        tools = await mcp.list_tools(server_name)
        for t in tools:
            all_tools.append(t)
            tool_server_map[t["name"]] = server_name

    yield StreamChunk(type="text", content=f"Found {len(all_tools)} tools. ")

    if not all_tools:
        yield StreamChunk(type="done", artifacts=[Artifact(name="no-tools", parts=[MessagePart(type="text", content="No tools available.")])])
        return

    yield StreamChunk(type="text", content="Selecting the best tool... ")

    # LLM picks tool
    tools_json = json.dumps([{"name": t["name"], "description": t.get("description", ""), "parameters": t.get("inputSchema", {}).get("properties", {})} for t in all_tools], indent=2)
    prompt = TOOL_PICKER_PROMPT.format(tools_json=tools_json)
    decision_raw = await llm_call(prompt, text)
    decision = _extract_json(decision_raw)

    if not decision or decision.get("tool_name") == "none":
        yield StreamChunk(type="done", artifacts=[Artifact(name="no-match", parts=[MessagePart(type="text", content="No suitable tool found.")])])
        return

    tool_name = decision["tool_name"]
    arguments = decision.get("arguments", {})
    server_name = tool_server_map.get(tool_name, "")

    yield StreamChunk(type="text", content=f"Calling **{tool_name}**({json.dumps(arguments)})... ")

    # Call tool
    result = await mcp.call_tool(server_name, tool_name, arguments)
    tool_data = result.get("data", result) if isinstance(result, dict) else result

    yield StreamChunk(type="text", content="Done! Formatting results.\n\n")

    # Build artifact with components (reuse same logic)
    artifacts = await _use_tool(mcp, text)
    yield StreamChunk(type="done", artifacts=artifacts)


app = create_a2a_app(
    name="MCP Explorer",
    description="Discover and use external tools via MCP. Connects to weather, crypto, news, and more.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
    streaming_handler_func=handle_streaming,
)
