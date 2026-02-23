"""Main SDK client for the A2A Marketplace."""

from __future__ import annotations

from typing import Any, AsyncIterator

import httpx

from .models import Agent, Balance, SearchResult, Task, Transaction
from .streaming import TaskStream


class MarketplaceError(Exception):
    """Raised when the API returns a non-2xx response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _raise_on_error(response: httpx.Response) -> None:
    """Raise *MarketplaceError* if the response is not 2xx."""
    if response.is_success:
        return
    try:
        detail = response.json().get("detail", response.text)
    except Exception:
        detail = response.text
    raise MarketplaceError(response.status_code, detail)


def _build_headers(api_key: str) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


# ---------------------------------------------------------------------------
# Resource classes
# ---------------------------------------------------------------------------

class AgentResource:
    """Operations on the ``/agents`` endpoint."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def _url(self, *parts: str) -> str:
        segments = "/".join(parts)
        return f"{self._base_url}/agents/{segments}" if segments else f"{self._base_url}/agents"

    def register(
        self,
        name: str,
        endpoint: str,
        skills: list[dict[str, Any]],
        pricing: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Agent:
        """Register a new agent in the marketplace."""
        payload: dict[str, Any] = {
            "name": name,
            "endpoint": endpoint,
            "skills": skills,
            "pricing": pricing or {},
            **kwargs,
        }
        resp = httpx.post(
            self._url(),
            json=payload,
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        return Agent.model_validate(resp.json())

    def list(
        self,
        page: int = 1,
        per_page: int = 20,
        category: str | None = None,
    ) -> list[Agent]:
        """List agents with optional pagination and filtering."""
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if category is not None:
            params["category"] = category
        resp = httpx.get(
            self._url(),
            params=params,
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        data = resp.json()
        # Support both a raw list and a paginated envelope with an "items" key.
        items = data if isinstance(data, list) else data.get("items", data)
        return [Agent.model_validate(item) for item in items]

    def get(self, agent_id: str) -> Agent:
        """Get a single agent by ID."""
        resp = httpx.get(
            self._url(agent_id),
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        return Agent.model_validate(resp.json())

    def update(self, agent_id: str, **kwargs: Any) -> Agent:
        """Update an existing agent."""
        resp = httpx.patch(
            self._url(agent_id),
            json=kwargs,
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        return Agent.model_validate(resp.json())

    def deactivate(self, agent_id: str) -> None:
        """Deactivate (soft-delete) an agent."""
        resp = httpx.post(
            self._url(agent_id, "deactivate"),
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)

    def card(self, agent_id: str) -> dict[str, Any]:
        """Fetch the A2A Agent Card for the given agent."""
        resp = httpx.get(
            self._url(agent_id, "card"),
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        return resp.json()


class TaskResource:
    """Operations on the ``/tasks`` endpoint."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def _url(self, *parts: str) -> str:
        segments = "/".join(parts)
        return f"{self._base_url}/tasks/{segments}" if segments else f"{self._base_url}/tasks"

    def create(
        self,
        provider_agent_id: str,
        skill_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> Task:
        """Create a new task."""
        payload: dict[str, Any] = {
            "provider_agent_id": provider_agent_id,
            "skill_id": skill_id,
            "messages": messages,
            **kwargs,
        }
        resp = httpx.post(
            self._url(),
            json=payload,
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        return Task.model_validate(resp.json())

    def get(self, task_id: str) -> Task:
        """Get a task by ID."""
        resp = httpx.get(
            self._url(task_id),
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        return Task.model_validate(resp.json())

    def list(
        self,
        agent_id: str | None = None,
        status: str | None = None,
    ) -> list[Task]:
        """List tasks, optionally filtered by agent or status."""
        params: dict[str, Any] = {}
        if agent_id is not None:
            params["agent_id"] = agent_id
        if status is not None:
            params["status"] = status
        resp = httpx.get(
            self._url(),
            params=params,
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("items", data)
        return [Task.model_validate(item) for item in items]

    def cancel(self, task_id: str) -> Task:
        """Cancel a running task."""
        resp = httpx.post(
            self._url(task_id, "cancel"),
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        return Task.model_validate(resp.json())

    def rate(self, task_id: str, score: float, comment: str = "") -> Task:
        """Rate a completed task."""
        payload: dict[str, Any] = {"score": score}
        if comment:
            payload["comment"] = comment
        resp = httpx.post(
            self._url(task_id, "rate"),
            json=payload,
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        return Task.model_validate(resp.json())

    async def stream(self, task_id: str) -> AsyncIterator[Task]:
        """Stream real-time task updates via WebSocket.

        Returns an async iterator that yields ``Task`` instances as the
        task progresses on the server.

        Usage::

            async for update in marketplace.tasks.stream("task-123"):
                print(update.status)
        """
        task_stream = TaskStream(
            base_url=self._base_url,
            task_id=task_id,
            api_key=self._api_key,
        )
        async for task in task_stream:
            yield task


class CreditResource:
    """Operations on the ``/credits`` endpoint."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def _url(self, *parts: str) -> str:
        segments = "/".join(parts)
        return f"{self._base_url}/credits/{segments}" if segments else f"{self._base_url}/credits"

    def balance(self) -> Balance:
        """Retrieve the current credit balance."""
        resp = httpx.get(
            self._url("balance"),
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        return Balance.model_validate(resp.json())

    def purchase(self, amount: float) -> Transaction:
        """Purchase credits."""
        resp = httpx.post(
            self._url("purchase"),
            json={"amount": amount},
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        return Transaction.model_validate(resp.json())

    def transactions(self, page: int = 1) -> list[Transaction]:
        """List credit transactions."""
        resp = httpx.get(
            self._url("transactions"),
            params={"page": page},
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("items", data)
        return [Transaction.model_validate(item) for item in items]


# ---------------------------------------------------------------------------
# Top-level client
# ---------------------------------------------------------------------------

class Marketplace:
    """Python SDK client for the A2A Marketplace.

    Usage::

        from a2a_marketplace import Marketplace

        mp = Marketplace(api_key="your-key")
        agents = mp.agents.list()
        results = mp.discover("translate English to French")
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "http://localhost:8000/api/v1",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

        self.agents = AgentResource(self._base_url, self._api_key)
        self.tasks = TaskResource(self._base_url, self._api_key)
        self.credits = CreditResource(self._base_url, self._api_key)

    def discover(
        self,
        query: str,
        **kwargs: Any,
    ) -> list[SearchResult]:
        """Discover agents matching a natural-language query.

        Sends a ``POST`` to ``/discover`` with a ``SearchQuery`` payload.
        """
        payload: dict[str, Any] = {"query": query, **kwargs}
        resp = httpx.post(
            f"{self._base_url}/discover",
            json=payload,
            headers=_build_headers(self._api_key),
        )
        _raise_on_error(resp)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("results", data)
        return [SearchResult.model_validate(item) for item in items]
