import time
import httpx
from config import settings

# Fields that are safe to cache — excludes secrets
_SAFE_CONNECTION_FIELDS = {
    "id", "owner_id", "platform", "agent_id", "skill_id", "status",
    "daily_credit_limit", "pause_on_limit", "low_balance_threshold", "config",
}

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
        """Return non-sensitive connection fields, cached for 60 s.

        bot_token and webhook_secret are intentionally excluded from the cache
        to avoid exposing secrets in a plain-dict memory structure.
        """
        cached = self._connection_cache.get(connection_id)
        if cached and time.time() - cached[1] < self._cache_ttl:
            return cached[0]

        resp = await self._client.get(f"/gateway/connections/{connection_id}")
        if resp.status_code != 200:
            return None
        data = resp.json()
        # Strip sensitive fields before caching
        safe_data = {k: v for k, v in data.items() if k in _SAFE_CONNECTION_FIELDS}
        self._connection_cache[connection_id] = (safe_data, time.time())
        return safe_data

    async def get_bot_token(self, connection_id: str) -> str | None:
        """Fetch the decrypted bot token on-demand. Never cached."""
        resp = await self._client.get(f"/gateway/connections/{connection_id}")
        if resp.status_code != 200:
            return None
        return resp.json().get("bot_token")

    async def charge_credits(self, connection_id: str, owner_id: str, credits: float, daily_credit_limit: int | None = None) -> dict:
        resp = await self._client.post("/gateway/charge", json={
            "connection_id": connection_id,
            "platform_user_id": "system",
            "credits": credits,
            "daily_credit_limit": daily_credit_limit,
        })
        return resp.json()

    async def log_message(self, data: dict) -> dict:
        resp = await self._client.post("/gateway/log-message", json=data)
        return resp.json()

    async def create_task(self, agent_id: str, skill_id: str | None, message: str, owner_id: str, callback_url: str) -> dict:
        """Create a task via the dedicated gateway endpoint (authenticated with X-Gateway-Key)."""
        resp = await self._client.post("/gateway/create-task", json={
            "owner_id": owner_id,
            "provider_agent_id": agent_id,
            "skill_id": skill_id,
            "message": message,
            "callback_url": callback_url,
        })
        if resp.status_code in (200, 201):
            return resp.json()
        return {"error": resp.text}

    def invalidate_cache(self, connection_id: str):
        self._connection_cache.pop(connection_id, None)
