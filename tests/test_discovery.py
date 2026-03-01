"""Tests for the agent discovery and search endpoints (/api/v1/discover)."""

import pytest
from httpx import AsyncClient

from tests.conftest import _make_agent_payload


# ------------------------------------------------------------------
# POST /api/v1/discover/ -- keyword search
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_keyword_search(client: AsyncClient, auth_headers: dict):
    """Searching for 'legal' should find an agent with 'legal' in its name."""
    # Register an agent with "legal" in the name
    payload = _make_agent_payload(
        name="Legal Document Analyzer",
        description="Analyzes legal contracts and extracts clauses",
        category="legal",
    )
    reg_resp = await client.post("/api/v1/agents/", json=payload, headers=auth_headers)
    assert reg_resp.status_code == 201

    # Search
    search_resp = await client.post(
        "/api/v1/discover/",
        json={"query": "legal", "mode": "keyword"},
        headers=auth_headers,
    )
    assert search_resp.status_code == 200

    body = search_resp.json()
    assert "matches" in body
    assert "total_candidates" in body
    assert "query_time_ms" in body
    assert body["total_candidates"] >= 1

    matched_names = [m["agent"]["name"] for m in body["matches"]]
    assert "Legal Document Analyzer" in matched_names


# ------------------------------------------------------------------
# POST /api/v1/discover/ -- filter by category
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_by_category(client: AsyncClient, auth_headers: dict):
    """Searching with a category filter should only return agents in that category."""
    # Register agents in two different categories
    legal_payload = _make_agent_payload(
        name="Legal Bot",
        category="legal",
        description="Legal assistant",
    )
    finance_payload = _make_agent_payload(
        name="Finance Bot",
        category="finance",
        description="Finance assistant",
    )

    resp_l = await client.post("/api/v1/agents/", json=legal_payload, headers=auth_headers)
    resp_f = await client.post("/api/v1/agents/", json=finance_payload, headers=auth_headers)
    assert resp_l.status_code == 201
    assert resp_f.status_code == 201

    # Search with category=legal
    search_resp = await client.post(
        "/api/v1/discover/",
        json={"query": "assistant", "mode": "keyword", "category": "legal"},
        headers=auth_headers,
    )
    assert search_resp.status_code == 200

    body = search_resp.json()
    categories_found = {m["agent"]["category"] for m in body["matches"]}
    # If results are returned, they should all be in the legal category
    if body["matches"]:
        assert categories_found == {"legal"}


# ------------------------------------------------------------------
# POST /api/v1/discover/ -- no results
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_no_results(client: AsyncClient, auth_headers: dict):
    """Searching for a completely nonexistent term should return empty matches."""
    search_resp = await client.post(
        "/api/v1/discover/",
        json={"query": "xyzzy_nonexistent_term_12345", "mode": "keyword"},
        headers=auth_headers,
    )
    assert search_resp.status_code == 200

    body = search_resp.json()
    assert body["matches"] == []
    assert body["total_candidates"] == 0


# ------------------------------------------------------------------
# GET /api/v1/discover/categories
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_categories(client: AsyncClient, auth_headers: dict):
    """Registering agents in different categories and listing should show them."""
    # Register agents in two categories
    await client.post(
        "/api/v1/agents/",
        json=_make_agent_payload(name="Cat Agent A", category="analytics"),
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/agents/",
        json=_make_agent_payload(name="Cat Agent B", category="creative"),
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/discover/categories")
    assert resp.status_code == 200

    categories = resp.json()
    assert isinstance(categories, list)
    category_names = [c["category"] for c in categories]
    assert "analytics" in category_names
    assert "creative" in category_names


# ------------------------------------------------------------------
# GET /api/v1/discover/skills/trending
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_trending_skills(client: AsyncClient, auth_headers: dict):
    """The trending skills endpoint should return a list."""
    # Register an agent so there is at least one skill in the database
    await client.post(
        "/api/v1/agents/",
        json=_make_agent_payload(name="Trending Skills Agent"),
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/discover/skills/trending")
    assert resp.status_code == 200

    skills = resp.json()
    assert isinstance(skills, list)
    if skills:
        assert "skill_id" in skills[0]
        assert "name" in skills[0]
        assert "task_count" in skills[0]
