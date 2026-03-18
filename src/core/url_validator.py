"""URL validation to prevent SSRF attacks."""
import ipaddress
import socket
from urllib.parse import urlparse

from src.core.exceptions import BadRequestError

_BLOCKED_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_public_url(url: str) -> str:
    """Validate that a URL is a public HTTPS address, not an internal/private IP."""
    parsed = urlparse(url)

    if parsed.scheme not in ("https", "http"):
        raise BadRequestError(detail="URL must use HTTPS or HTTP scheme")

    hostname = parsed.hostname
    if not hostname:
        raise BadRequestError(detail="Invalid URL: no hostname")

    try:
        addrs = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        raise BadRequestError(detail=f"Cannot resolve hostname: {hostname}")

    for family, _, _, _, sockaddr in addrs:
        ip = ipaddress.ip_address(sockaddr[0])
        for blocked in _BLOCKED_RANGES:
            if ip in blocked:
                raise BadRequestError(
                    detail="URL resolves to a private/internal address — not allowed"
                )

    return url
