# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""DID (Decentralized Identifier) generation and verification.

Implements did:wba method for agent identity. Each agent gets:
  did:wba:api.aidigitalcrew.com:agents:{agent_id}

Key format: Ed25519 (signing + verification)
Storage: private key encrypted with Fernet, public key stored raw.
"""

import base64
from uuid import UUID

from nacl.signing import SigningKey, VerifyKey

from src.core.encryption import decrypt_value, encrypt_value

DID_DOMAIN = "api.aidigitalcrew.com"


def generate_did_keypair() -> tuple[bytes, bytes]:
    """Generate an Ed25519 keypair for DID.

    Returns:
        (public_key_bytes, private_key_bytes)
    """
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    return bytes(verify_key), bytes(signing_key)


def agent_did(agent_id: UUID) -> str:
    """Generate the DID string for an agent."""
    return f"did:wba:{DID_DOMAIN}:agents:{agent_id}"


def build_did_document(agent_id: UUID, public_key: bytes, endpoint: str) -> dict:
    """Build a W3C DID Core compliant DID document.

    Args:
        agent_id: Agent UUID
        public_key: Ed25519 public key bytes (32 bytes)
        endpoint: Agent's service endpoint URL
    """
    did = agent_did(agent_id)
    pub_b64 = base64.b64encode(public_key).decode()

    return {
        "@context": [
            "https://www.w3.org/ns/did/v1",
            "https://w3id.org/security/suites/ed25519-2020/v1",
        ],
        "id": did,
        "verificationMethod": [
            {
                "id": f"{did}#key-1",
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyBase64": pub_b64,
            }
        ],
        "authentication": [f"{did}#key-1"],
        "service": [
            {
                "id": f"{did}#agent-service",
                "type": "AgentService",
                "serviceEndpoint": endpoint,
            },
            {
                "id": f"{did}#a2a",
                "type": "A2AService",
                "serviceEndpoint": f"https://{DID_DOMAIN}/api/v1/a2a",
            },
        ],
    }


def build_agent_description(
    agent_id: UUID,
    name: str,
    description: str,
    skills: list[dict],
    endpoint: str,
    mcp_server_url: str | None = None,
) -> dict:
    """Build a JSON-LD agent description (ANP Agent Description Protocol).

    Returns an ADP-format document with metadata, capabilities, and interfaces.
    """
    did = agent_did(agent_id)
    interfaces = [
        {
            "protocol": "A2A",
            "endpoint": f"https://{DID_DOMAIN}/api/v1/a2a",
            "version": "1.0",
        },
    ]
    if mcp_server_url:
        interfaces.append({
            "protocol": "MCP",
            "endpoint": mcp_server_url,
            "version": "1.0",
        })

    return {
        "@context": "https://schema.org",
        "@type": "SoftwareAgent",
        "identifier": did,
        "name": name,
        "description": description,
        "provider": {
            "@type": "Organization",
            "name": "AI Digital Crew",
            "url": "https://aidigitalcrew.com",
        },
        "capabilities": [
            {
                "name": s.get("name", s.get("skill_key", "")),
                "description": s.get("description", ""),
                "inputModes": s.get("input_modes", ["text"]),
                "outputModes": s.get("output_modes", ["text"]),
            }
            for s in skills
        ],
        "interfaces": interfaces,
        "security": {
            "authentication": "did:wba",
            "verificationMethod": f"{did}#key-1",
        },
    }


def encrypt_private_key(private_key: bytes) -> str:
    """Encrypt a private key for storage using platform Fernet encryption."""
    return encrypt_value(base64.b64encode(private_key).decode())


def decrypt_private_key(encrypted: str) -> bytes | None:
    """Decrypt a stored private key. Returns None on failure."""
    decrypted = decrypt_value(encrypted)
    if not decrypted:
        return None
    return base64.b64decode(decrypted)


def sign_message(private_key: bytes, message: bytes) -> bytes:
    """Sign a message with the agent's Ed25519 private key."""
    signing_key = SigningKey(private_key)
    return signing_key.sign(message).signature


def verify_signature(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """Verify a signature against a public key."""
    try:
        verify_key = VerifyKey(public_key)
        verify_key.verify(message, signature)
        return True
    except Exception:
        return False
