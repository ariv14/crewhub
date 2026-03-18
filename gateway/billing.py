"""Credit billing via CrewHub API."""
import httpx
from config import CREWHUB_API_URL, CREWHUB_SERVICE_KEY

_http_client: httpx.AsyncClient | None = None


def set_http_client(client: httpx.AsyncClient):
    """Set the shared HTTP client (called from lifespan)."""
    global _http_client
    _http_client = client


def _get_client() -> httpx.AsyncClient:
    """Return the shared client, or create a fallback if not yet initialized."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30, limits=httpx.Limits(max_connections=100))
    return _http_client


async def get_developer_balance(owner_id: str) -> float:
    """Get developer's credit balance."""
    client = _get_client()
    resp = await client.get(
        f"{CREWHUB_API_URL}/api/v1/credits/balance",
        headers={"X-API-Key": CREWHUB_SERVICE_KEY},
        params={"user_id": owner_id},
    )
    if resp.status_code == 200:
        data = resp.json()
        return float(data.get("available", 0))
    return 0.0


async def create_task(agent_id: str, skill_id: str | None, message: str,
                      owner_id: str, callback_url: str,
                      idempotency_key: str | None = None) -> dict | None:
    """Create a task on CrewHub, developer pays credits."""
    payload = {
        "provider_agent_id": agent_id,
        "message": message,
    }
    if skill_id:
        payload["skill_id"] = skill_id

    headers = {"X-API-Key": CREWHUB_SERVICE_KEY, "Content-Type": "application/json"}
    if callback_url:
        payload["callback_url"] = callback_url
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    client = _get_client()
    resp = await client.post(
        f"{CREWHUB_API_URL}/api/v1/tasks/",
        json=payload,
        headers=headers,
    )
    if resp.status_code in (200, 201):
        return resp.json()
    return None


async def get_connection(connection_id: str) -> dict | None:
    """Fetch a single channel connection config from CrewHub API."""
    client = _get_client()
    resp = await client.get(
        f"{CREWHUB_API_URL}/api/v1/gateway/connections/{connection_id}",
        headers={"X-API-Key": CREWHUB_SERVICE_KEY},
    )
    if resp.status_code == 200:
        return resp.json()
    return None


async def log_message(connection_id: str, data: dict):
    """Log a channel message to CrewHub API."""
    client = _get_client()
    await client.post(
        f"{CREWHUB_API_URL}/api/v1/gateway/log-message",
        json={"connection_id": connection_id, **data},
        headers={"X-API-Key": CREWHUB_SERVICE_KEY},
    )


async def get_today_usage(connection_id: str) -> float:
    """Get today's credit usage for a connection."""
    client = _get_client()
    resp = await client.get(
        f"{CREWHUB_API_URL}/api/v1/gateway/today-usage/{connection_id}",
        headers={"X-API-Key": CREWHUB_SERVICE_KEY},
    )
    if resp.status_code == 200:
        return float(resp.json().get("credits_used", 0))
    return 0.0


async def update_connection_status(connection_id: str, status: str, reason: str = ""):
    """Update a connection's status (e.g. pause on limit)."""
    client = _get_client()
    await client.post(
        f"{CREWHUB_API_URL}/api/v1/gateway/update-status",
        json={"connection_id": connection_id, "status": status, "reason": reason},
        headers={"X-API-Key": CREWHUB_SERVICE_KEY},
    )
