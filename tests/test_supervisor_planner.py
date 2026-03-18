"""Tests for the supervisor planner service with mocked LLM calls."""

import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.supervisor import (
    ApprovePlanRequest,
    SupervisorPlanRequest,
    SupervisorPlan,
    SupervisorPlanStep,
)
from src.services.supervisor_planner import SupervisorPlannerService


def _mock_agent(agent_id=None, name="Test Agent", category="engineering"):
    """Create a mock Agent with skills."""
    agent = MagicMock()
    agent.id = agent_id or uuid.uuid4()
    agent.name = name
    agent.status = "active"
    agent.category = category
    agent.reputation_score = 4.5
    skill = MagicMock()
    skill.id = uuid.uuid4()
    skill.name = "test-skill"
    skill.skill_key = "test-skill"
    skill.description = "A test skill"
    skill.avg_credits = 5.0
    agent.skills = [skill]
    return agent, skill


def _mock_llm_response(agents_and_skills):
    """Build a valid LLM plan response JSON string from agent/skill pairs."""
    steps = []
    for i, (agent, skill) in enumerate(agents_and_skills):
        steps.append(
            {
                "agent_id": str(agent.id),
                "skill_id": str(skill.id),
                "agent_name": agent.name,
                "skill_name": skill.name,
                "step_group": i,
                "input_mode": "chain",
                "instructions": f"Step {i} instructions",
                "label": f"Step {i}",
                "confidence": 0.9,
            }
        )
    return json.dumps(
        {
            "name": "Test Workflow",
            "description": "A test workflow",
            "steps": steps,
        }
    )


def _make_db_mock():
    """Create a mock async DB session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_generate_plan_valid_goal():
    """generate_plan returns valid steps with real agent IDs."""
    agent, skill = _mock_agent()
    db = _make_db_mock()

    # Mock both execute calls: 1st = DELETE expired, 2nd = SELECT agents
    delete_result = MagicMock()
    select_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [agent]
    select_result.scalars.return_value = scalars_mock
    db.execute = AsyncMock(side_effect=[delete_result, select_result])

    service = SupervisorPlannerService(db)
    request = SupervisorPlanRequest(goal="Summarize a document for me please")

    with patch(
        "src.services.supervisor_planner.completion", new_callable=AsyncMock
    ) as mock_llm, patch(
        "src.services.supervisor_planner.select"
    ), patch(
        "src.services.supervisor_planner.delete"
    ), patch(
        "src.services.supervisor_planner.selectinload"
    ):
        mock_llm.return_value = _mock_llm_response([(agent, skill)])
        plan = await service.generate_plan(request, uuid.uuid4())

    assert plan.name == "Test Workflow"
    assert len(plan.steps) == 1
    assert plan.steps[0].agent_id == agent.id
    assert plan.steps[0].skill_id == skill.id
    assert plan.total_estimated_credits > 0
    assert plan.plan_id is not None


@pytest.mark.asyncio
async def test_generate_plan_filters_invalid_agents():
    """Steps with nonexistent agent IDs are filtered out."""
    agent, skill = _mock_agent()
    db = _make_db_mock()

    delete_result = MagicMock()
    select_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [agent]
    select_result.scalars.return_value = scalars_mock
    db.execute = AsyncMock(side_effect=[delete_result, select_result])

    service = SupervisorPlannerService(db)
    request = SupervisorPlanRequest(goal="Do something complex for me please")

    # LLM returns a step with a fake agent ID and one valid step
    fake_response = json.dumps(
        {
            "name": "Test",
            "description": "Test",
            "steps": [
                {
                    "agent_id": str(uuid.uuid4()),
                    "skill_id": str(uuid.uuid4()),
                    "step_group": 0,
                    "confidence": 0.9,
                    "label": "Fake",
                    "input_mode": "chain",
                    "instructions": "Fake step",
                },
                {
                    "agent_id": str(agent.id),
                    "skill_id": str(skill.id),
                    "step_group": 1,
                    "confidence": 0.9,
                    "label": "Real",
                    "input_mode": "chain",
                    "instructions": "Real step",
                },
            ],
        }
    )

    with patch(
        "src.services.supervisor_planner.completion", new_callable=AsyncMock
    ) as mock_llm, patch(
        "src.services.supervisor_planner.select"
    ), patch(
        "src.services.supervisor_planner.delete"
    ), patch(
        "src.services.supervisor_planner.selectinload"
    ):
        mock_llm.return_value = fake_response
        plan = await service.generate_plan(request, uuid.uuid4())

    # Only the valid step should remain
    assert len(plan.steps) == 1
    assert plan.steps[0].agent_id == agent.id


@pytest.mark.asyncio
async def test_generate_plan_no_agents_raises():
    """Raises ValueError when no active agents available."""
    db = _make_db_mock()

    delete_result = MagicMock()
    select_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    select_result.scalars.return_value = scalars_mock
    db.execute = AsyncMock(side_effect=[delete_result, select_result])

    service = SupervisorPlannerService(db)
    request = SupervisorPlanRequest(goal="This should fail because no agents")

    with patch(
        "src.services.supervisor_planner.select"
    ), patch(
        "src.services.supervisor_planner.delete"
    ), patch(
        "src.services.supervisor_planner.selectinload"
    ):
        with pytest.raises(ValueError, match="No active agents"):
            await service.generate_plan(request, uuid.uuid4())


@pytest.mark.asyncio
async def test_generate_plan_all_invalid_steps_raises():
    """Raises ValueError when LLM returns only invalid agent references."""
    agent, skill = _mock_agent()
    db = _make_db_mock()

    delete_result = MagicMock()
    select_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [agent]
    select_result.scalars.return_value = scalars_mock
    db.execute = AsyncMock(side_effect=[delete_result, select_result])

    service = SupervisorPlannerService(db)
    request = SupervisorPlanRequest(goal="This will have no valid steps at all")

    # LLM returns only fake agent/skill IDs
    fake_response = json.dumps(
        {
            "name": "Bad Plan",
            "description": "All steps invalid",
            "steps": [
                {
                    "agent_id": str(uuid.uuid4()),
                    "skill_id": str(uuid.uuid4()),
                    "step_group": 0,
                    "confidence": 0.9,
                    "label": "Fake",
                    "input_mode": "chain",
                    "instructions": "Fake step",
                },
            ],
        }
    )

    with patch(
        "src.services.supervisor_planner.completion", new_callable=AsyncMock
    ) as mock_llm, patch(
        "src.services.supervisor_planner.select"
    ), patch(
        "src.services.supervisor_planner.delete"
    ), patch(
        "src.services.supervisor_planner.selectinload"
    ):
        mock_llm.return_value = fake_response
        with pytest.raises(ValueError, match="no valid steps"):
            await service.generate_plan(request, uuid.uuid4())


@pytest.mark.asyncio
async def test_generate_plan_stores_plan_record():
    """generate_plan stores a SupervisorPlanRecord in the database."""
    agent, skill = _mock_agent()
    db = _make_db_mock()

    delete_result = MagicMock()
    select_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [agent]
    select_result.scalars.return_value = scalars_mock
    db.execute = AsyncMock(side_effect=[delete_result, select_result])

    service = SupervisorPlannerService(db)
    request = SupervisorPlanRequest(goal="Summarize a document for me please")

    with patch(
        "src.services.supervisor_planner.completion", new_callable=AsyncMock
    ) as mock_llm, patch(
        "src.services.supervisor_planner.select"
    ), patch(
        "src.services.supervisor_planner.delete"
    ), patch(
        "src.services.supervisor_planner.selectinload"
    ):
        mock_llm.return_value = _mock_llm_response([(agent, skill)])
        plan = await service.generate_plan(request, uuid.uuid4())

    # Verify db.add was called (to persist the plan record)
    assert db.add.called
    assert db.flush.called
    assert plan.plan_id is not None


@pytest.mark.asyncio
async def test_generate_plan_clamps_confidence():
    """Confidence values are clamped to [0, 1]."""
    agent, skill = _mock_agent()
    db = _make_db_mock()

    delete_result = MagicMock()
    select_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [agent]
    select_result.scalars.return_value = scalars_mock
    db.execute = AsyncMock(side_effect=[delete_result, select_result])

    service = SupervisorPlannerService(db)
    request = SupervisorPlanRequest(goal="Summarize a document for me please")

    # LLM returns out-of-range confidence
    response = json.dumps(
        {
            "name": "Test",
            "description": "Test",
            "steps": [
                {
                    "agent_id": str(agent.id),
                    "skill_id": str(skill.id),
                    "step_group": 0,
                    "confidence": 5.0,  # out of range, should be clamped to 1.0
                    "label": "Clamped",
                    "input_mode": "chain",
                    "instructions": "Test",
                },
            ],
        }
    )

    with patch(
        "src.services.supervisor_planner.completion", new_callable=AsyncMock
    ) as mock_llm, patch(
        "src.services.supervisor_planner.select"
    ), patch(
        "src.services.supervisor_planner.delete"
    ), patch(
        "src.services.supervisor_planner.selectinload"
    ):
        mock_llm.return_value = response
        plan = await service.generate_plan(request, uuid.uuid4())

    assert plan.steps[0].confidence == 1.0


@pytest.mark.asyncio
async def test_approve_plan_creates_workflow():
    """approve_plan converts plan to saved Workflow."""
    agent, skill = _mock_agent()
    plan_id = uuid.uuid4()
    user_id = uuid.uuid4()

    plan_record = MagicMock()
    plan_record.id = plan_id
    plan_record.user_id = user_id
    plan_record.goal = "Test goal"
    plan_record.llm_provider = "groq"
    plan_record.status = "draft"
    plan_record.plan_data = {
        "name": "Test Workflow",
        "description": "Test",
        "steps": [
            {
                "agent_id": str(agent.id),
                "skill_id": str(skill.id),
                "step_group": 0,
                "input_mode": "chain",
                "instructions": "Do something",
                "label": "Step 1",
            }
        ],
    }

    db = _make_db_mock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = plan_record
    db.execute = AsyncMock(return_value=mock_result)

    service = SupervisorPlannerService(db)
    request = ApprovePlanRequest(plan_id=str(plan_id))

    with patch(
        "src.services.supervisor_planner.select"
    ):
        workflow = await service.approve_plan(request, user_id)

    assert workflow.pattern_type == "supervisor"
    assert workflow.supervisor_config["plan_status"] == "approved"
    # db.add called for workflow + 1 step = at least 2 calls
    assert db.add.call_count >= 2


@pytest.mark.asyncio
async def test_approve_plan_not_found_raises():
    """approve_plan raises ValueError for unknown plan."""
    db = _make_db_mock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    service = SupervisorPlannerService(db)
    request = ApprovePlanRequest(plan_id=str(uuid.uuid4()))

    with patch(
        "src.services.supervisor_planner.select"
    ):
        with pytest.raises(ValueError, match="Plan not found"):
            await service.approve_plan(request, uuid.uuid4())
