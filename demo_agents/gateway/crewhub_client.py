import time
import httpx
from config import settings

class CrewHubClient:
    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=settings.crewhub_api_url,
            headers={"X-Gateway-Key": settings.gateway_service_key},
            timeout=30.0,
        )
        self._connection_cache: dict[str, tuple[dict, float]] = {}
        self._cache_ttl = 60  # seconds

    async def get_connection(self, connection_id: str) -> dict | None:
        # Check cache
        cached = self._connection_cache.get(connection_id)
        if cached and time.time() - cached[1] < self._cache_ttl:
            return cached[0]

        resp = await self._client.get(f"/gateway/connections/{connection_id}")
        if resp.status_code != 200:
            return None
        data = resp.json()
        self._connection_cache[connection_id] = (data, time.time())
        return data

    async def charge_credits(self, connection_id: str, owner_id: str, credits: float, message_text: str, daily_credit_limit: int | None = None) -> dict:
        resp = await self._client.post("/gateway/charge", json={
            "connection_id": connection_id,
            "platform_user_id": "system",
            "credits": credits,
            "message_text": message_text,
            "daily_credit_limit": daily_credit_limit,
        })
        return resp.json()

    async def log_message(self, data: dict) -> dict:
        resp = await self._client.post("/gateway/log-message", json=data)
        return resp.json()

    async def create_task(self, agent_id: str, skill_id: str | None, message: str, owner_id: str, callback_url: str) -> dict:
        # Task creation uses the gateway service key as an API key
        resp = await self._client.post("/tasks/", json={
            "provider_agent_id": agent_id,
            "skill_id": skill_id,
            "message": message,
            "callback_url": callback_url,
        }, headers={"X-API-Key": f"gateway_{settings.gateway_service_key[:32]}"})
        if resp.status_code in (200, 201):
            return resp.json()
        return {"error": resp.text}

    def invalidate_cache(self, connection_id: str):
        self._connection_cache.pop(connection_id, None)
