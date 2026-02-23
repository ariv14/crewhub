"""API key lookup helper.

This module is separated to avoid circular imports. It provides a database
lookup for API keys used in authentication. The implementation will be
connected to the actual database layer once the models and repositories
are in place.
"""


async def lookup_user_by_api_key(api_key: str) -> dict | None:
    """Look up a user by their API key.

    This is a placeholder that will be wired to the database once the
    repository layer is available.

    Args:
        api_key: The API key string (e.g., 'a2a_...').

    Returns:
        dict with 'id' and 'email' if found, None otherwise.
    """
    # TODO: Wire to actual DB query via repository layer
    # Example: user = await api_key_repo.get_user_by_key(api_key)
    return None
