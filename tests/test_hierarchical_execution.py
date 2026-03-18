# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Tests for hierarchical workflow execution helpers."""

from unittest.mock import MagicMock

from src.services.workflow_execution import WorkflowExecutionService


def test_collect_child_output_single_step():
    """Collects output from last step group."""
    child_run = MagicMock()
    sr1 = MagicMock(step_group=0, output_text="Step 0 output")
    sr2 = MagicMock(step_group=1, output_text="Step 1 output")
    child_run.step_runs = [sr1, sr2]

    service = WorkflowExecutionService.__new__(WorkflowExecutionService)
    result = service._collect_child_output(child_run)
    assert result == "Step 1 output"


def test_collect_child_output_parallel_group():
    """Collects and joins outputs from parallel steps in last group."""
    child_run = MagicMock()
    sr1 = MagicMock(step_group=0, output_text="Research A")
    sr2 = MagicMock(step_group=0, output_text="Research B")
    child_run.step_runs = [sr1, sr2]

    service = WorkflowExecutionService.__new__(WorkflowExecutionService)
    result = service._collect_child_output(child_run)
    assert "Research A" in result
    assert "Research B" in result
    assert "---" in result


def test_collect_child_output_empty():
    """Returns empty string for run with no step runs."""
    child_run = MagicMock()
    child_run.step_runs = []

    service = WorkflowExecutionService.__new__(WorkflowExecutionService)
    result = service._collect_child_output(child_run)
    assert result == ""
