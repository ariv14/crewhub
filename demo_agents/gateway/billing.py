import logging

logger = logging.getLogger(__name__)

async def check_and_charge(client, connection: dict, message_text: str, platform_surcharge: float = 0):
    """Atomic credit check + charge. Returns (ok, error_reason)."""
    cost = 1 + platform_surcharge

    result = await client.charge_credits(
        connection_id=str(connection["id"]),
        owner_id=str(connection["owner_id"]),
        credits=cost,
        message_text=message_text,
        daily_credit_limit=connection.get("daily_credit_limit"),
    )

    if not result.get("success"):
        error = result.get("error", "charge_failed")
        logger.warning("Charge failed for connection %s: %s", connection["id"], error)
        return False, error
    return True, None
