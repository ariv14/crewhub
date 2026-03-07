"""Telemetry service — logs user behavior events to the database."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.telemetry import TelemetryEvent

logger = logging.getLogger(__name__)


class TelemetryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
        self,
        event_name: str,
        user_id: str | None = None,
        properties: dict | None = None,
    ) -> None:
        """Log a single telemetry event."""
        if not settings.telemetry_enabled:
            return

        try:
            event = TelemetryEvent(
                user_id=user_id,
                event_name=event_name,
                properties=properties,
            )
            self.db.add(event)
            await self.db.flush()
        except Exception:
            logger.warning("Failed to log telemetry event: %s", event_name, exc_info=True)

    async def log_batch(
        self,
        events: list[dict],
        user_id: str | None = None,
    ) -> int:
        """Log a batch of telemetry events. Returns count of events logged."""
        if not settings.telemetry_enabled:
            return 0

        count = 0
        for event_data in events:
            try:
                event = TelemetryEvent(
                    user_id=user_id,
                    event_name=event_data.get("name", "unknown"),
                    properties=event_data.get("properties"),
                )
                self.db.add(event)
                count += 1
            except Exception:
                logger.warning("Failed to log telemetry event", exc_info=True)

        if count > 0:
            await self.db.flush()

        return count
