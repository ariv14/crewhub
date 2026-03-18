"""Security validation tests for supervisor planning schemas."""

import pytest
from pydantic import ValidationError

from src.schemas.supervisor import SupervisorPlanRequest


def test_goal_too_short():
    """Rejects goals shorter than 10 chars."""
    with pytest.raises(ValidationError):
        SupervisorPlanRequest(goal="short")


def test_goal_too_long():
    """Rejects goals longer than 2000 chars."""
    with pytest.raises(ValidationError):
        SupervisorPlanRequest(goal="x" * 2001)


def test_valid_goal():
    """Accepts valid goal."""
    req = SupervisorPlanRequest(
        goal="Research competitor pricing strategies and summarize findings"
    )
    assert req.goal is not None


def test_optional_fields():
    """Optional fields default to None."""
    req = SupervisorPlanRequest(goal="A valid goal that is long enough")
    assert req.llm_provider is None
    assert req.max_credits is None


def test_max_credits_must_be_positive():
    """Rejects max_credits below 1."""
    with pytest.raises(ValidationError):
        SupervisorPlanRequest(
            goal="A valid goal that is long enough",
            max_credits=0,
        )


def test_max_credits_accepts_valid():
    """Accepts valid max_credits."""
    req = SupervisorPlanRequest(
        goal="A valid goal that is long enough",
        max_credits=50.0,
    )
    assert req.max_credits == 50.0


def test_goal_exactly_10_chars():
    """Accepts goal at minimum boundary (10 chars)."""
    req = SupervisorPlanRequest(goal="a" * 10)
    assert len(req.goal) == 10


def test_goal_exactly_2000_chars():
    """Accepts goal at maximum boundary (2000 chars)."""
    req = SupervisorPlanRequest(goal="a" * 2000)
    assert len(req.goal) == 2000
