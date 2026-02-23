"""Permission checking utilities."""

from uuid import UUID

from src.core.exceptions import ForbiddenError


def check_agent_owner(agent_owner_id: UUID, current_user_id: UUID) -> None:
    """Verify that the current user is the owner of the agent.

    Args:
        agent_owner_id: The UUID of the agent's owner.
        current_user_id: The UUID of the currently authenticated user.

    Raises:
        ForbiddenError: If the user is not the agent owner.
    """
    if agent_owner_id != current_user_id:
        raise ForbiddenError(detail="You do not own this agent")


def check_account_owner(account_owner_id: UUID, current_user_id: UUID) -> None:
    """Verify that the current user is the owner of the account.

    Args:
        account_owner_id: The UUID of the account's owner.
        current_user_id: The UUID of the currently authenticated user.

    Raises:
        ForbiddenError: If the user is not the account owner.
    """
    if account_owner_id != current_user_id:
        raise ForbiddenError(detail="You do not own this account")
