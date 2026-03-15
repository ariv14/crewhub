# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""ANP authentication — DID-based HTTP request signing and verification.

Agents sign requests with their Ed25519 private key. Recipients verify
by fetching the sender's DID document and checking the signature.

Signature scheme:
  - Header: X-DID-Signature: <base64-encoded-signature>
  - Header: X-DID-Sender: <did-string>
  - Signed payload: METHOD + PATH + BODY (canonical form)
"""

import base64
import logging

import httpx
from fastapi import Header, HTTPException, Request

from src.core.did import verify_signature

logger = logging.getLogger(__name__)


def _canonical_message(method: str, path: str, body: bytes) -> bytes:
    """Build the canonical message to sign/verify."""
    return f"{method.upper()}\n{path}\n".encode() + body


async def verify_anp_signature(
    request: Request,
    x_did_signature: str | None = Header(None, alias="X-DID-Signature"),
    x_did_sender: str | None = Header(None, alias="X-DID-Sender"),
) -> dict | None:
    """FastAPI dependency: verify ANP DID-based signature on incoming requests.

    Returns the sender's DID string if valid, or None if no ANP headers present.
    Raises HTTPException(401) if headers are present but invalid.
    """
    # If no ANP headers, skip (allows non-ANP authenticated requests)
    if not x_did_signature or not x_did_sender:
        return None

    body = await request.body()
    message = _canonical_message(request.method, request.url.path, body)

    try:
        signature = base64.b64decode(x_did_signature)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid X-DID-Signature encoding")

    # Fetch sender's DID document to get their public key
    public_key = await _resolve_did_public_key(x_did_sender)
    if not public_key:
        raise HTTPException(status_code=401, detail=f"Could not resolve DID: {x_did_sender}")

    if not verify_signature(public_key, message, signature):
        raise HTTPException(status_code=401, detail="Invalid ANP signature")

    return {"did": x_did_sender}


async def _resolve_did_public_key(did: str) -> bytes | None:
    """Resolve a did:wba DID to its public key by fetching the DID document.

    DID format: did:wba:<domain>:agents:<agent_id>
    Resolves to: https://<domain>/api/v1/agents/<agent_id>/did.json
    """
    import ipaddress
    import socket

    parts = did.split(":")
    if len(parts) < 5 or parts[0] != "did" or parts[1] != "wba":
        return None

    domain = parts[2]

    # SSRF protection: block internal/private domains and IPs
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "metadata.google.internal"}
    if domain.lower() in blocked_hosts:
        logger.warning("DID resolution blocked: internal hostname %s", domain)
        return None
    if domain.endswith(".internal") or domain.endswith(".local"):
        logger.warning("DID resolution blocked: internal domain %s", domain)
        return None

    # Resolve hostname to IP and check for private ranges
    try:
        ip = ipaddress.ip_address(domain)
    except ValueError:
        # It's a hostname — resolve it and check
        try:
            resolved = socket.getaddrinfo(domain, 443, proto=socket.IPPROTO_TCP)
            for _, _, _, _, addr in resolved:
                ip = ipaddress.ip_address(addr[0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    logger.warning("DID resolution blocked: %s resolves to private IP %s", domain, ip)
                    return None
        except socket.gaierror:
            pass  # Let httpx handle DNS failure
    else:
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            logger.warning("DID resolution blocked: private IP %s", domain)
            return None

    # Remaining parts form the path: agents/<agent_id>
    path = "/".join(parts[3:])
    url = f"https://{domain}/api/v1/{path}/did.json"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            doc = resp.json()
            # Extract public key from verificationMethod
            methods = doc.get("verificationMethod", [])
            if not methods:
                return None
            pub_b64 = methods[0].get("publicKeyBase64")
            if not pub_b64:
                return None
            return base64.b64decode(pub_b64)
    except Exception as e:
        logger.error(f"Failed to resolve DID {did}: {e}")
        return None


def sign_request(private_key: bytes, method: str, path: str, body: bytes) -> str:
    """Sign an HTTP request for ANP authentication.

    Returns the base64-encoded signature to be set as X-DID-Signature header.
    """
    from src.core.did import sign_message
    message = _canonical_message(method, path, body)
    signature = sign_message(private_key, message)
    return base64.b64encode(signature).decode()
