"""Tests for LLM API key CRUD endpoints (/api/v1/llm-keys)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.encryption import decrypt_value
from src.models.user import User


# ------------------------------------------------------------------
# GET /api/v1/llm-keys/ — empty state
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_keys_empty(client: AsyncClient, auth_headers: dict):
    """New user should have no keys set."""
    resp = await client.get("/api/v1/llm-keys/", headers=auth_headers)
    assert resp.status_code == 200

    body = resp.json()
    assert "keys" in body
    for key_entry in body["keys"]:
        assert key_entry["is_set"] is False
        assert key_entry["masked_key"] == ""


# ------------------------------------------------------------------
# PUT /api/v1/llm-keys/{provider} — set key
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_openai_key(client: AsyncClient, auth_headers: dict):
    """Setting an OpenAI key should return is_set=True and a masked key."""
    resp = await client.put(
        "/api/v1/llm-keys/openai",
        json={"provider": "openai", "api_key": "sk-test123456789"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    body = resp.json()
    assert body["provider"] == "openai"
    assert body["is_set"] is True
    assert "..." in body["masked_key"]


@pytest.mark.asyncio
async def test_set_key_updates_existing(client: AsyncClient, auth_headers: dict):
    """Setting a key twice should replace the first key."""
    await client.put(
        "/api/v1/llm-keys/openai",
        json={"provider": "openai", "api_key": "sk-first-key-abcdef"},
        headers=auth_headers,
    )
    resp2 = await client.put(
        "/api/v1/llm-keys/openai",
        json={"provider": "openai", "api_key": "sk-second-key-xyz99"},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    # The masked key should reflect the second key's suffix
    assert resp2.json()["masked_key"].endswith("z99")


@pytest.mark.asyncio
async def test_list_keys_after_set(client: AsyncClient, auth_headers: dict):
    """After setting openai and gemini keys, both should appear as is_set."""
    await client.put(
        "/api/v1/llm-keys/openai",
        json={"provider": "openai", "api_key": "sk-openai-test"},
        headers=auth_headers,
    )
    await client.put(
        "/api/v1/llm-keys/gemini",
        json={"provider": "gemini", "api_key": "gemini-test-key"},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/llm-keys/", headers=auth_headers)
    assert resp.status_code == 200

    keys_by_provider = {k["provider"]: k for k in resp.json()["keys"]}
    assert keys_by_provider["openai"]["is_set"] is True
    assert keys_by_provider["gemini"]["is_set"] is True
    # Providers not set should remain False
    assert keys_by_provider["cohere"]["is_set"] is False


# ------------------------------------------------------------------
# DELETE /api/v1/llm-keys/{provider}
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_key(client: AsyncClient, auth_headers: dict):
    """Deleting a key should make it show as not set."""
    await client.put(
        "/api/v1/llm-keys/openai",
        json={"provider": "openai", "api_key": "sk-to-delete"},
        headers=auth_headers,
    )
    del_resp = await client.delete("/api/v1/llm-keys/openai", headers=auth_headers)
    assert del_resp.status_code == 200

    list_resp = await client.get("/api/v1/llm-keys/", headers=auth_headers)
    keys_by_provider = {k["provider"]: k for k in list_resp.json()["keys"]}
    assert keys_by_provider["openai"]["is_set"] is False


@pytest.mark.asyncio
async def test_delete_nonexistent_key(client: AsyncClient, auth_headers: dict):
    """Deleting a key that was never set should still return 200 (idempotent)."""
    resp = await client.delete("/api/v1/llm-keys/openai", headers=auth_headers)
    assert resp.status_code == 200


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_provider(client: AsyncClient, auth_headers: dict):
    """Using an invalid provider name should return 400."""
    resp = await client.put(
        "/api/v1/llm-keys/invalid_provider",
        json={"provider": "invalid_provider", "api_key": "sk-test"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Invalid provider" in resp.json()["detail"]


# ------------------------------------------------------------------
# Masking format
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_key_masking_format(client: AsyncClient, auth_headers: dict):
    """Keys > 10 chars show first 4 + '...' + last 3."""
    resp = await client.put(
        "/api/v1/llm-keys/openai",
        json={"provider": "openai", "api_key": "sk-abcdefghijklmnop"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    masked = resp.json()["masked_key"]
    assert masked == "sk-a...nop"


# ------------------------------------------------------------------
# Encryption verification
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_key_encryption_roundtrip(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """The raw DB value should be encrypted, not plaintext."""
    plaintext_key = "sk-super-secret-key-12345"
    await client.put(
        "/api/v1/llm-keys/openai",
        json={"provider": "openai", "api_key": plaintext_key},
        headers=auth_headers,
    )

    # Read raw DB value
    result = await db_session.execute(select(User))
    users = result.scalars().all()
    # Find the user that has llm_api_keys set
    test_user = next(u for u in users if u.llm_api_keys and "openai" in u.llm_api_keys)
    raw_value = test_user.llm_api_keys["openai"]

    # Raw value should NOT be the plaintext
    assert raw_value != plaintext_key
    # But decrypting it should recover the plaintext
    assert decrypt_value(raw_value) == plaintext_key


# ------------------------------------------------------------------
# Unauthenticated access
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_rejected(client: AsyncClient):
    """All LLM key endpoints should return 401 without auth."""
    assert (await client.get("/api/v1/llm-keys/")).status_code == 401
    assert (
        await client.put(
            "/api/v1/llm-keys/openai",
            json={"provider": "openai", "api_key": "sk-x"},
        )
    ).status_code == 401
    assert (await client.delete("/api/v1/llm-keys/openai")).status_code == 401
