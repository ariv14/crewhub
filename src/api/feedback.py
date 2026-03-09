"""Public feedback endpoint — forwards user feedback to Discord."""

import logging

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    message: str = Field(..., min_length=3, max_length=1000)
    page: str = Field(default="/", max_length=200)
    email: str = Field(default="", max_length=200)


@router.post("", status_code=202)
async def submit_feedback(data: FeedbackCreate):
    """Accept user feedback and forward to Discord webhook."""
    webhook_url = settings.discord_feedback_webhook
    if not webhook_url:
        logger.warning("Feedback received but DISCORD_FEEDBACK_WEBHOOK not set")
        return {"accepted": True, "webhook_configured": False}

    embed = {
        "title": "New Feedback",
        "color": 0x7C3AED,  # Purple
        "fields": [
            {"name": "Message", "value": data.message[:1000]},
            {"name": "Page", "value": data.page, "inline": True},
        ],
    }
    if data.email:
        embed["fields"].append({"name": "Email", "value": data.email, "inline": True})

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(webhook_url, json={"embeds": [embed]})
    except Exception as e:
        logger.warning("Failed to forward feedback to Discord", exc_info=True)
        return {"accepted": True, "webhook_error": str(e)}

    return {"accepted": True, "webhook_configured": True}
