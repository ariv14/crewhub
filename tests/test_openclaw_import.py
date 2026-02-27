"""Tests for OpenClaw skill importer."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from src.services.openclaw_importer import OpenClawImporter


def test_sanitize_text_strips_html():
    """HTML tags should be stripped from imported text."""
    raw = '<script>alert("xss")</script><b>Bold text</b> and <a href="#">link</a>'
    clean = OpenClawImporter.sanitize_text(raw)
    assert "<script>" not in clean
    assert "<b>" not in clean
    assert "<a " not in clean
    assert "Bold text" in clean
    assert "link" in clean


def test_sanitize_text_truncates():
    """Text longer than max_length should be truncated."""
    long_text = "a" * 20000
    clean = OpenClawImporter.sanitize_text(long_text, max_length=10000)
    assert len(clean) == 10000


def test_parse_manifest_extracts_fields():
    """Parser should extract name, description, and endpoint from markdown."""
    manifest = """# My Awesome Skill

A skill that does amazing things with data analysis.

## Endpoint
https://api.example.com/skill

## Input Modes
text, data

## Output Modes
text
"""
    result = OpenClawImporter.parse_manifest(manifest)
    assert result["name"] == "My Awesome Skill"
    assert "amazing things" in result["description"]
    assert result["endpoint"] == "https://api.example.com/skill"


def test_parse_manifest_handles_minimal():
    """Parser should handle manifests with missing sections gracefully."""
    manifest = "# Simple Skill\n\nJust a simple skill."
    result = OpenClawImporter.parse_manifest(manifest)
    assert result["name"] == "Simple Skill"
    assert "simple skill" in result["description"].lower()


@pytest.mark.asyncio
async def test_import_endpoint_rejects_bad_domain(client: AsyncClient, auth_headers: dict):
    """Import endpoint should reject URLs from non-allowed domains."""
    resp = await client.post(
        "/api/v1/import/openclaw",
        json={
            "skill_url": "https://evil.com/malicious-skill",
            "pricing": {"model": "per_task", "credits": 0, "license_type": "open"},
            "category": "general",
            "tags": ["test"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_import_endpoint_success(client: AsyncClient, auth_headers: dict):
    """Import from allowed domain should create an inactive agent."""
    mock_manifest = """# Test Imported Skill

A skill for testing imports.

## Endpoint
https://api.example.com/openclaw-skill

## Input Modes
text

## Output Modes
text
"""
    with patch(
        "src.services.openclaw_importer.OpenClawImporter.fetch_manifest",
        new_callable=AsyncMock,
        return_value=mock_manifest,
    ):
        resp = await client.post(
            "/api/v1/import/openclaw",
            json={
                "skill_url": "https://clawhub.io/skills/test-skill",
                "pricing": {"model": "per_task", "credits": 0, "license_type": "open"},
                "category": "general",
                "tags": ["imported"],
            },
            headers=auth_headers,
        )
    assert resp.status_code == 201

    data = resp.json()
    assert data["status"] == "inactive"
    assert data["source"] == "openclaw"
