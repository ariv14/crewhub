"""Credit billing via CrewHub API."""
import httpx
from config import CREWHUB_API_URL, CREWHUB_SERVICE_KEY

async def get_developer_balance(owner_id: str) -> float:
    """Get developer's credit balance."""
    async with httpx.AsyncClient(timeout=30) as client:
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

    async with httpx.AsyncClient(timeout=30) as client:
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
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{CREWHUB_API_URL}/api/v1/gateway/connections/{connection_id}",
            headers={"X-API-Key": CREWHUB_SERVICE_KEY},
        )
        if resp.status_code == 200:
            return resp.json()
        return None

async def log_message(connection_id: str, data: dict):
    """Log a channel message to CrewHub API."""
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{CREWHUB_API_URL}/api/v1/gateway/log-message",
            json={"connection_id": connection_id, **data},
            headers={"X-API-Key": CREWHUB_SERVICE_KEY},
        )
