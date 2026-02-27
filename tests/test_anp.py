"""Tests for ANP protocol — DID documents, agent descriptions, and discovery."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_did_document_generation():
    """DID document generation returns correct W3C format."""
    import uuid
    from src.core.did import build_did_document, generate_did_keypair

    agent_id = uuid.uuid4()
    pub_key, _ = generate_did_keypair()

    doc = build_did_document(agent_id, pub_key, "https://example.com/agent")

    assert doc["@context"][0] == "https://www.w3.org/ns/did/v1"
    assert doc["id"].startswith("did:wba:")
    assert str(agent_id) in doc["id"]
    assert len(doc["verificationMethod"]) == 1
    assert doc["verificationMethod"][0]["type"] == "Ed25519VerificationKey2020"
    assert len(doc["authentication"]) == 1
    assert len(doc["service"]) == 2


@pytest.mark.asyncio
async def test_did_keypair_sign_verify():
    """Ed25519 sign and verify roundtrip works correctly."""
    from src.core.did import generate_did_keypair, sign_message, verify_signature

    pub_key, priv_key = generate_did_keypair()
    message = b"test message to sign"

    signature = sign_message(priv_key, message)
    assert verify_signature(pub_key, message, signature)

    # Tampered message should fail
    assert not verify_signature(pub_key, b"wrong message", signature)


@pytest.mark.asyncio
async def test_did_key_encryption_roundtrip():
    """Private key encrypt/decrypt roundtrip preserves the key."""
    from src.core.did import decrypt_private_key, encrypt_private_key, generate_did_keypair

    _, priv_key = generate_did_keypair()
    encrypted = encrypt_private_key(priv_key)
    decrypted = decrypt_private_key(encrypted)

    assert decrypted == priv_key


@pytest.mark.asyncio
async def test_agent_description_format():
    """Agent description returns JSON-LD format."""
    import uuid
    from src.core.did import build_agent_description

    desc = build_agent_description(
        agent_id=uuid.uuid4(),
        name="Test Agent",
        description="A test agent",
        skills=[{"name": "summarize", "description": "Summarize text", "input_modes": ["text"], "output_modes": ["text"]}],
        endpoint="https://example.com",
        mcp_server_url="https://example.com/mcp",
    )

    assert desc["@context"] == "https://schema.org"
    assert desc["@type"] == "SoftwareAgent"
    assert desc["name"] == "Test Agent"
    assert len(desc["capabilities"]) == 1
    assert len(desc["interfaces"]) == 2  # A2A + MCP


@pytest.mark.asyncio
async def test_anp_auth_canonical_message():
    """ANP auth canonical message format is consistent."""
    from src.core.anp_auth import _canonical_message

    msg = _canonical_message("POST", "/api/v1/a2a", b'{"test": true}')
    assert msg == b'POST\n/api/v1/a2a\n{"test": true}'


@pytest.mark.asyncio
async def test_anp_auth_sign_and_verify_request():
    """Request signing and verification roundtrip."""
    from src.core.anp_auth import sign_request
    from src.core.did import generate_did_keypair, verify_signature

    pub_key, priv_key = generate_did_keypair()
    import base64
    from src.core.anp_auth import _canonical_message

    sig_b64 = sign_request(priv_key, "POST", "/api/v1/a2a", b'{"task": "test"}')
    signature = base64.b64decode(sig_b64)
    message = _canonical_message("POST", "/api/v1/a2a", b'{"task": "test"}')

    assert verify_signature(pub_key, message, signature)


@pytest.mark.asyncio
async def test_well_known_agent_descriptions(client: AsyncClient):
    """/.well-known/agent-descriptions returns JSON-LD CollectionPage."""
    resp = await client.get("/.well-known/agent-descriptions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["@type"] == "CollectionPage"
    assert "itemListElement" in data


@pytest.mark.asyncio
async def test_agent_did_document_404_without_key(client: AsyncClient):
    """DID document endpoint returns 404 for nonexistent agent."""
    resp = await client.get("/api/v1/agents/00000000-0000-0000-0000-000000000000/did.json")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_registered_agent_has_did(
    client: AsyncClient, auth_headers: dict, registered_agent: dict
):
    """A newly registered agent should have a DID assigned."""
    assert registered_agent.get("did") is not None
    assert registered_agent["did"].startswith("did:wba:")


@pytest.mark.asyncio
async def test_registered_agent_did_document(
    client: AsyncClient, auth_headers: dict, registered_agent: dict
):
    """A registered agent's DID document should be fetchable."""
    agent_id = registered_agent["id"]
    resp = await client.get(f"/api/v1/agents/{agent_id}/did.json")
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["id"].endswith(agent_id)
    assert len(doc["verificationMethod"]) > 0


@pytest.mark.asyncio
async def test_a2a_rejects_bad_anp_signature(client: AsyncClient):
    """A2A endpoint rejects requests with invalid ANP DID signature."""
    resp = await client.post(
        "/api/v1/a2a",
        json={
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"id": "00000000-0000-0000-0000-000000000000"},
            "id": 1,
        },
        headers={
            "X-DID-Signature": "aW52YWxpZC1zaWduYXR1cmU=",  # base64("invalid-signature")
            "X-DID-Sender": "did:wba:example.com:agents:fake-agent",
        },
    )
    # Should be 401 because the DID can't be resolved / signature is invalid
    assert resp.status_code == 401
