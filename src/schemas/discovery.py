from enum import Enum
from typing import Optional

from pydantic import BaseModel

from src.schemas.agent import AgentResponse


class SearchMode(str, Enum):
    keyword = "keyword"
    semantic = "semantic"
    capability = "capability"
    intent = "intent"


class SearchQuery(BaseModel):
    query: str
    mode: SearchMode = SearchMode.keyword
    category: Optional[str] = None
    tags: list[str] = []
    max_latency_ms: Optional[int] = None
    max_credits: Optional[float] = None
    input_modes: list[str] = []
    output_modes: list[str] = []
    min_reputation: float = 0
    limit: int = 10


class AgentMatch(BaseModel):
    agent: AgentResponse
    relevance_score: float
    match_reason: str


class DiscoveryResponse(BaseModel):
    matches: list[AgentMatch]
    total_candidates: int
    query_time_ms: float
    hint: str | None = None
