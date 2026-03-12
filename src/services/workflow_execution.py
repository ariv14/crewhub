"""Workflow execution engine — runs multi-step agent pipelines."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import InsufficientCreditsError, MarketplaceError
from src.models.task import Task
from src.models.workflow import Workflow, WorkflowRun, WorkflowStep, WorkflowStepRun
from src.schemas.task import TaskCreate as TaskCreateSchema, TaskMessage, MessagePart

logger = logging.getLogger(__name__)

# Fallback timeouts when workflow has no user-configured values
DEFAULT_WORKFLOW_TIMEOUT = 1800  # 30 minutes
DEFAULT_STEP_TIMEOUT = 120  # 2 minutes


class WorkflowExecutionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Execute — kick off a workflow run
    # ------------------------------------------------------------------

    async def execute_workflow(
        self, workflow_id: UUID, user_id: UUID, input_message: str, schedule_id: UUID | None = None
    ) -> WorkflowRun:
        from src.services.workflow_service import WorkflowService

        wf_svc = WorkflowService(self.db)
        wf = await wf_svc.get_workflow(workflow_id)

        if not wf.steps:
            raise MarketplaceError(status_code=400, detail="Workflow has no steps")

        # Build snapshot of workflow definition (includes timeout config)
        snapshot = {
            "name": wf.name,
            "timeout_seconds": wf.timeout_seconds or DEFAULT_WORKFLOW_TIMEOUT,
            "step_timeout_seconds": wf.step_timeout_seconds or DEFAULT_STEP_TIMEOUT,
            "steps": [
                {
                    "id": str(s.id),
                    "agent_id": str(s.agent_id),
                    "skill_id": str(s.skill_id),
                    "step_group": s.step_group,
                    "position": s.position,
                    "input_mode": s.input_mode,
                    "input_template": s.input_template,
                    "label": s.label,
                    "instructions": s.instructions,
                    "agent_name": s.agent.name if s.agent else None,
                    "skill_name": s.skill.name if s.skill else None,
                }
                for s in wf.steps
            ],
        }

        # Upfront cost estimate
        total_estimate = self._estimate_cost(wf)
        if wf.max_total_credits and total_estimate > wf.max_total_credits:
            raise MarketplaceError(
                status_code=400,
                detail=f"Estimated cost ({total_estimate} credits) exceeds workflow limit "
                       f"({wf.max_total_credits} credits)",
            )

        # Check user balance
        from src.services.credit_ledger import CreditLedgerService
        ledger = CreditLedgerService(self.db)
        balance_info = await ledger.get_balance(user_id)
        available = balance_info["available"]
        if total_estimate > 0 and available < total_estimate:
            raise InsufficientCreditsError(
                detail=f"Estimated cost is {total_estimate} credits but available balance is {available}"
            )

        # Create workflow run
        run = WorkflowRun(
            workflow_id=workflow_id,
            user_id=user_id,
            schedule_id=schedule_id,
            status="running",
            current_step_group=0,
            input_message=input_message,
            workflow_snapshot=snapshot,
        )
        self.db.add(run)
        await self.db.flush()

        # Create step runs for ALL steps (pending)
        step_groups = {}
        for s in wf.steps:
            step_groups.setdefault(s.step_group, []).append(s)

        for group_num, steps in step_groups.items():
            for step in steps:
                sr = WorkflowStepRun(
                    run_id=run.id,
                    step_id=step.id,
                    step_group=group_num,
                    status="pending",
                )
                self.db.add(sr)

        await self.db.commit()
        await self.db.refresh(run)

        # Dispatch step_group 0
        await self._dispatch_step_group(run, wf, group_num=0, input_text=input_message)

        return run

    # ------------------------------------------------------------------
    # Pump — advance all running workflows
    # ------------------------------------------------------------------

    async def pump_running_workflows(self) -> None:
        now = datetime.now(timezone.utc)

        result = await self.db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.status == "running")
            .options(selectinload(WorkflowRun.step_runs))
            .limit(20)
        )
        runs = list(result.scalars().unique().all())

        for run in runs:
            try:
                await self._pump_single_run(run, now)
            except Exception:
                logger.exception("Error pumping workflow run %s", run.id)
                run.status = "failed"
                run.error = "Internal error during execution"
                run.completed_at = now

        await self.db.commit()

    async def _pump_single_run(self, run: WorkflowRun, now: datetime) -> None:
        # Read timeout from snapshot (user-configured), fallback to defaults
        snapshot = run.workflow_snapshot or {}
        wf_timeout = snapshot.get("timeout_seconds", DEFAULT_WORKFLOW_TIMEOUT)
        step_timeout = snapshot.get("step_timeout_seconds", DEFAULT_STEP_TIMEOUT)

        # Check workflow-level timeout
        created = run.created_at.replace(
            tzinfo=timezone.utc if run.created_at.tzinfo is None else run.created_at.tzinfo
        )
        elapsed = (now - created).total_seconds()
        if elapsed > wf_timeout:
            run.status = "failed"
            run.error = (
                f"Workflow timed out after {int(elapsed)}s "
                f"(limit: {wf_timeout}s). "
                f"You can increase the timeout in workflow settings."
            )
            run.completed_at = now
            # Mark any running steps as timed out too
            for sr in run.step_runs:
                if sr.status == "running":
                    sr.status = "failed"
                    sr.error = "Workflow-level timeout reached"
                    sr.completed_at = now
            self._tally_credits(run)
            return

        current_group = run.current_step_group
        group_step_runs = [sr for sr in run.step_runs if sr.step_group == current_group]

        if not group_step_runs:
            run.status = "failed"
            run.error = "No step runs found for current group"
            run.completed_at = now
            return

        # Check per-step timeouts for running steps
        self._check_step_timeouts(group_step_runs, step_timeout, now, snapshot)

        # Check if all step runs in current group are terminal
        all_terminal = all(sr.status in ("completed", "failed") for sr in group_step_runs)
        if not all_terminal:
            # Check tasks for status updates
            await self._sync_step_run_statuses(group_step_runs, snapshot)
            # Re-check step timeouts after syncing
            self._check_step_timeouts(group_step_runs, step_timeout, now, snapshot)
            all_terminal = all(sr.status in ("completed", "failed") for sr in group_step_runs)
            if not all_terminal:
                return

        # Check for failures — collect error details
        failed_steps = [sr for sr in group_step_runs if sr.status == "failed"]
        if failed_steps:
            error_details = []
            for sr in failed_steps:
                step_info = self._step_info_from_snapshot(snapshot, sr.step_id)
                label = step_info.get("agent_name", "Unknown") if step_info else "Unknown"
                if sr.error:
                    error_details.append(f"{label}: {sr.error}")
                else:
                    error_details.append(f"{label}: failed (no details)")
            run.status = "failed"
            run.error = f"Step {current_group + 1} failed — " + "; ".join(error_details)
            run.completed_at = now
            self._tally_credits(run)
            return

        # All completed — advance to next group
        all_groups = sorted(set(sr.step_group for sr in run.step_runs))
        current_idx = all_groups.index(current_group)

        if current_idx + 1 >= len(all_groups):
            # All groups done
            run.status = "completed"
            run.completed_at = now
            self._tally_credits(run)
            return

        # Advance to next group
        next_group = all_groups[current_idx + 1]
        run.current_step_group = next_group

        # Collect output from completed group
        prev_output = self._collect_group_output(group_step_runs)

        # We need the workflow to resolve step details
        wf_result = await self.db.execute(
            select(Workflow)
            .where(Workflow.id == run.workflow_id)
            .options(
                selectinload(Workflow.steps).selectinload(WorkflowStep.agent),
                selectinload(Workflow.steps).selectinload(WorkflowStep.skill),
            )
        )
        wf = wf_result.scalar_one_or_none()

        if wf:
            await self._dispatch_step_group(
                run, wf, group_num=next_group,
                input_text=run.input_message, prev_output=prev_output,
            )

    def _check_step_timeouts(
        self,
        step_runs: list[WorkflowStepRun],
        step_timeout: int,
        now: datetime,
        snapshot: dict,
    ) -> None:
        for sr in step_runs:
            if sr.status != "running" or not sr.started_at:
                continue
            started = sr.started_at.replace(
                tzinfo=timezone.utc if sr.started_at.tzinfo is None else sr.started_at.tzinfo
            )
            elapsed = (now - started).total_seconds()
            if elapsed > step_timeout:
                step_info = self._step_info_from_snapshot(snapshot, sr.step_id)
                agent_name = step_info.get("agent_name", "Unknown") if step_info else "Unknown"
                skill_name = step_info.get("skill_name", "Unknown") if step_info else "Unknown"
                sr.status = "failed"
                sr.error = (
                    f"Step timed out after {int(elapsed)}s (limit: {step_timeout}s). "
                    f"Agent '{agent_name}' with skill '{skill_name}' did not respond in time. "
                    f"The agent may be offline or overloaded."
                )
                sr.completed_at = now
                logger.warning(
                    "Step run %s timed out after %ds (agent: %s, skill: %s)",
                    sr.id, int(elapsed), agent_name, skill_name,
                )

    def _step_info_from_snapshot(self, snapshot: dict, step_id: UUID | None) -> dict | None:
        if not step_id or not snapshot.get("steps"):
            return None
        step_id_str = str(step_id)
        for s in snapshot["steps"]:
            if s.get("id") == step_id_str:
                return s
        return None

    async def _sync_step_run_statuses(
        self, step_runs: list[WorkflowStepRun], snapshot: dict
    ) -> None:
        for sr in step_runs:
            if sr.status in ("completed", "failed") or not sr.task_id:
                continue
            result = await self.db.execute(
                select(Task).where(Task.id == sr.task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                continue

            task_status = task.status.value if hasattr(task.status, "value") else str(task.status)

            if task_status == "completed":
                sr.status = "completed"
                sr.completed_at = datetime.now(timezone.utc)
                sr.output_text = self._extract_task_output(task)
                sr.credits_charged = task.credits_charged
            elif task_status in ("failed", "canceled"):
                sr.status = "failed"
                sr.completed_at = datetime.now(timezone.utc)
                step_info = self._step_info_from_snapshot(snapshot, sr.step_id)
                agent_name = step_info.get("agent_name", "Unknown") if step_info else "Unknown"
                sr.error = (
                    f"Task {task_status} — agent '{agent_name}' "
                    f"could not complete the request."
                )

    # ------------------------------------------------------------------
    # Dispatch helpers
    # ------------------------------------------------------------------

    async def _dispatch_step_group(
        self,
        run: WorkflowRun,
        wf: Workflow,
        group_num: int,
        input_text: str,
        prev_output: str | None = None,
    ) -> None:
        from src.services.task_broker import TaskBrokerService

        broker = TaskBrokerService(self.db)
        group_steps = [s for s in wf.steps if s.step_group == group_num]
        group_step_runs = [sr for sr in run.step_runs if sr.step_group == group_num]

        # Map step_id -> step_run for quick lookup
        sr_by_step = {sr.step_id: sr for sr in group_step_runs}

        # Collect all previous step outputs for custom templates
        all_outputs = {}
        for sr in run.step_runs:
            if sr.status == "completed" and sr.output_text:
                all_outputs[sr.step_group] = sr.output_text

        for step in group_steps:
            resolved_input = self._resolve_input(
                step, input_text, prev_output, all_outputs
            )
            final_input = self._apply_instructions(resolved_input, step.instructions)

            message = TaskMessage(
                role="user",
                parts=[MessagePart(type="text", content=final_input)],
            )
            task_data = TaskCreateSchema(
                provider_agent_id=step.agent_id,
                skill_id=str(step.skill_id),
                messages=[message],
                confirmed=True,
            )

            try:
                task = await broker.create_task(
                    data=task_data, user_id=run.user_id
                )
                sr = sr_by_step.get(step.id)
                if sr:
                    sr.task_id = task.id
                    sr.status = "running"
                    sr.started_at = datetime.now(timezone.utc)
            except Exception as exc:
                logger.exception(
                    "Failed to dispatch step %s in workflow run %s", step.id, run.id
                )
                sr = sr_by_step.get(step.id)
                if sr:
                    sr.status = "failed"
                    sr.error = (
                        f"Failed to dispatch task to agent "
                        f"'{step.agent.name if step.agent else 'Unknown'}': {exc}"
                    )
                    sr.completed_at = datetime.now(timezone.utc)

        await self.db.commit()

    def _apply_instructions(self, base_text: str, instructions: str | None) -> str:
        """Prepend per-step instructions to the resolved input text."""
        if not instructions or not instructions.strip():
            return base_text
        return (
            f"## Instructions\n{instructions.strip()}\n\n"
            f"## Task\n{base_text}"
        )

    def _resolve_input(
        self,
        step: WorkflowStep,
        original_input: str,
        prev_output: str | None,
        all_outputs: dict[int, str],
    ) -> str:
        mode = step.input_mode or "chain"

        if mode == "original":
            return original_input
        elif mode == "custom" and step.input_template:
            result = step.input_template
            result = result.replace("{{input}}", original_input)
            result = result.replace("{{prev_output}}", prev_output or "")
            for group_num, output in all_outputs.items():
                result = result.replace(f"{{{{step_{group_num}_output}}}}", output)
            return result
        else:
            # chain (default) — use previous output if available, else original
            return prev_output if prev_output else original_input

    def _collect_group_output(self, step_runs: list[WorkflowStepRun]) -> str:
        outputs = []
        for sr in sorted(step_runs, key=lambda x: x.step_group):
            if sr.output_text:
                outputs.append(sr.output_text)
        return "\n\n---\n\n".join(outputs) if outputs else ""

    def _extract_task_output(self, task: Task) -> str:
        if task.artifacts:
            parts = []
            for artifact in task.artifacts:
                if isinstance(artifact, dict):
                    for part in artifact.get("parts", []):
                        if isinstance(part, dict) and part.get("type") == "text":
                            # A2A artifacts use "content" field; fall back to "data"
                            text = part.get("content") or part.get("data") or ""
                            parts.append(text)
            return "\n".join(parts) if parts else ""
        return ""

    def _estimate_cost(self, wf: Workflow) -> int:
        total = 0
        for step in wf.steps:
            if step.agent and step.skill:
                avg = getattr(step.skill, "avg_credits", None)
                total += int(avg) if avg else 1
            else:
                total += 1
        return total

    def _tally_credits(self, run: WorkflowRun) -> None:
        total = Decimal("0")
        for sr in run.step_runs:
            if sr.credits_charged:
                total += sr.credits_charged
        run.total_credits_charged = total

    # ------------------------------------------------------------------
    # Cancel run
    # ------------------------------------------------------------------

    async def cancel_run(self, run_id: UUID, user_id: UUID) -> WorkflowRun:
        result = await self.db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .options(selectinload(WorkflowRun.step_runs))
        )
        run = result.scalar_one_or_none()
        if not run:
            raise MarketplaceError(status_code=404, detail="Workflow run not found")
        if run.user_id != user_id:
            raise MarketplaceError(status_code=403, detail="Not your workflow run")
        if run.status != "running":
            raise MarketplaceError(status_code=400, detail="Run is not in running state")

        now = datetime.now(timezone.utc)
        run.status = "canceled"
        run.completed_at = now
        for sr in run.step_runs:
            if sr.status in ("pending", "running"):
                sr.status = "failed"
                sr.error = "Canceled by user"
                sr.completed_at = now
        self._tally_credits(run)
        await self.db.commit()
        return run

    # ------------------------------------------------------------------
    # Cancel individual step run
    # ------------------------------------------------------------------

    async def cancel_step_run(
        self, run_id: UUID, step_run_id: UUID, user_id: UUID
    ) -> WorkflowRun:
        result = await self.db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .options(selectinload(WorkflowRun.step_runs))
        )
        run = result.scalar_one_or_none()
        if not run:
            raise MarketplaceError(status_code=404, detail="Workflow run not found")
        if run.user_id != user_id:
            raise MarketplaceError(status_code=403, detail="Not your workflow run")
        if run.status != "running":
            raise MarketplaceError(status_code=400, detail="Run is not in running state")

        target_sr = None
        for sr in run.step_runs:
            if sr.id == step_run_id:
                target_sr = sr
                break

        if not target_sr:
            raise MarketplaceError(status_code=404, detail="Step run not found")
        if target_sr.status not in ("pending", "running"):
            raise MarketplaceError(
                status_code=400,
                detail=f"Step is already {target_sr.status}, cannot cancel"
            )

        now = datetime.now(timezone.utc)
        snapshot = run.workflow_snapshot or {}
        step_info = self._step_info_from_snapshot(snapshot, target_sr.step_id)
        agent_name = step_info.get("agent_name", "Unknown") if step_info else "Unknown"

        target_sr.status = "failed"
        target_sr.error = f"Canceled by user (agent: {agent_name})"
        target_sr.completed_at = now

        await self.db.commit()

        # Re-query with eager-loaded step_runs (refresh doesn't load relations in async)
        result2 = await self.db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .options(selectinload(WorkflowRun.step_runs))
        )
        return result2.scalar_one()

    # ------------------------------------------------------------------
    # Startup recovery
    # ------------------------------------------------------------------

    async def recover_stale_runs(self) -> int:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.status == "running")
            .options(selectinload(WorkflowRun.step_runs))
        )
        runs = list(result.scalars().unique().all())

        count = 0
        for run in runs:
            run.status = "failed"
            run.error = "Process restarted during execution"
            run.completed_at = now
            for sr in run.step_runs:
                if sr.status == "running":
                    sr.status = "failed"
                    sr.error = "Process restarted during execution"
                    sr.completed_at = now
            count += 1

        if count:
            await self.db.commit()
            logger.info("Recovered %d stale workflow runs after restart", count)
        return count
