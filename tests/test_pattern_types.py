# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Tests for workflow pattern types and step validation."""

import uuid

import pytest

from src.schemas.workflow import WorkflowCreate, WorkflowStepCreate


def test_create_workflow_manual():
    """Default pattern_type is manual."""
    wf = WorkflowCreate(name="Test", steps=[
        WorkflowStepCreate(agent_id=uuid.uuid4(), skill_id=uuid.uuid4())
    ])
    assert wf.pattern_type == "manual"


def test_create_workflow_hierarchical():
    """Can create hierarchical workflow with sub_workflow_id."""
    wf = WorkflowCreate(name="Test", pattern_type="hierarchical", steps=[
        WorkflowStepCreate(sub_workflow_id=uuid.uuid4())
    ])
    assert wf.pattern_type == "hierarchical"
    assert wf.steps[0].sub_workflow_id is not None


def test_create_workflow_supervisor():
    """Can create supervisor workflow with config."""
    wf = WorkflowCreate(
        name="Test", pattern_type="supervisor",
        supervisor_config={"goal": "test", "plan_status": "draft"},
        steps=[]
    )
    assert wf.pattern_type == "supervisor"
    assert wf.supervisor_config["goal"] == "test"


def test_manual_rejects_invalid_pattern():
    """Invalid pattern_type is rejected."""
    with pytest.raises(Exception):
        WorkflowCreate(name="Test", pattern_type="invalid", steps=[])


def test_step_xor_both_set():
    """Rejects step with both agent_id+skill_id AND sub_workflow_id."""
    with pytest.raises(Exception):
        WorkflowStepCreate(
            agent_id=uuid.uuid4(), skill_id=uuid.uuid4(),
            sub_workflow_id=uuid.uuid4()
        )


def test_step_xor_neither_set():
    """Rejects step with neither agent_id nor sub_workflow_id."""
    with pytest.raises(Exception):
        WorkflowStepCreate()


def test_step_agent_only_valid():
    """Step with only agent_id+skill_id is valid."""
    step = WorkflowStepCreate(agent_id=uuid.uuid4(), skill_id=uuid.uuid4())
    assert step.agent_id is not None
    assert step.sub_workflow_id is None


def test_step_sub_workflow_only_valid():
    """Step with only sub_workflow_id is valid."""
    step = WorkflowStepCreate(sub_workflow_id=uuid.uuid4())
    assert step.sub_workflow_id is not None
    assert step.agent_id is None
