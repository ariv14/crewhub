"""Scheduler service — process due schedules and dispatch runs."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ForbiddenError, MarketplaceError, NotFoundError
from src.models.schedule import Schedule
from src.schemas.schedule import ScheduleCreate, ScheduleUpdate

logger = logging.getLogger(__name__)


def compute_next_run(cron_expression: str, tz_name: str, after: datetime | None = None) -> datetime | None:
    """Compute next run time from cron expression."""
    try:
        from croniter import croniter
    except ImportError:
        logger.warning("croniter not installed — cannot compute next run")
        return None

    if cron_expression == "@once":
        return None

    import zoneinfo
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except (KeyError, Exception):
        tz = zoneinfo.ZoneInfo("UTC")

    base = after or datetime.now(timezone.utc)
    base_local = base.astimezone(tz)
    cron = croniter(cron_expression, base_local)
    next_local = cron.get_next(datetime)
    return next_local.astimezone(timezone.utc)


class SchedulerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_schedule(self, owner_id: UUID, data: ScheduleCreate) -> Schedule:
        # Validate cron expression
        if data.cron_expression != "@once":
            try:
                from croniter import croniter
                if not croniter.is_valid(data.cron_expression):
                    raise MarketplaceError(status_code=400, detail="Invalid cron expression")
            except ImportError:
                pass

        next_run = compute_next_run(data.cron_expression, data.timezone)

        schedule = Schedule(
            owner_id=owner_id,
            name=data.name,
            schedule_type=data.schedule_type,
            target_id=data.target_id,
            task_params=data.task_params,
            cron_expression=data.cron_expression,
            timezone=data.timezone,
            input_message=data.input_message,
            is_active=data.is_active,
            next_run_at=next_run,
            max_runs=data.max_runs,
            credit_minimum=data.credit_minimum,
        )
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def get_schedule(self, schedule_id: UUID) -> Schedule:
        result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise NotFoundError("Schedule not found")
        return schedule

    async def list_my_schedules(self, owner_id: UUID) -> tuple[list[Schedule], int]:
        count_q = select(func.count()).select_from(Schedule).where(
            Schedule.owner_id == owner_id
        )
        total = (await self.db.execute(count_q)).scalar_one()

        q = (
            select(Schedule)
            .where(Schedule.owner_id == owner_id)
            .order_by(Schedule.created_at.desc())
        )
        result = await self.db.execute(q)
        schedules = list(result.scalars().all())
        return schedules, total

    async def update_schedule(
        self, schedule_id: UUID, owner_id: UUID, data: ScheduleUpdate
    ) -> Schedule:
        schedule = await self.get_schedule(schedule_id)
        if schedule.owner_id != owner_id:
            raise ForbiddenError("You do not own this schedule")

        if data.name is not None:
            schedule.name = data.name
        if data.input_message is not None:
            schedule.input_message = data.input_message
        if data.is_active is not None:
            schedule.is_active = data.is_active
        if data.max_runs is not None:
            schedule.max_runs = data.max_runs
        if data.credit_minimum is not None:
            schedule.credit_minimum = data.credit_minimum
        if data.max_consecutive_failures is not None:
            schedule.max_consecutive_failures = data.max_consecutive_failures

        if data.cron_expression is not None:
            if data.cron_expression != "@once":
                try:
                    from croniter import croniter
                    if not croniter.is_valid(data.cron_expression):
                        raise MarketplaceError(status_code=400, detail="Invalid cron expression")
                except ImportError:
                    pass
            schedule.cron_expression = data.cron_expression
            schedule.next_run_at = compute_next_run(
                data.cron_expression, data.timezone or schedule.timezone
            )

        if data.timezone is not None:
            schedule.timezone = data.timezone
            schedule.next_run_at = compute_next_run(
                schedule.cron_expression, data.timezone
            )

        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def delete_schedule(self, schedule_id: UUID, owner_id: UUID) -> None:
        schedule = await self.get_schedule(schedule_id)
        if schedule.owner_id != owner_id:
            raise ForbiddenError("You do not own this schedule")
        await self.db.delete(schedule)
        await self.db.commit()

    async def pause_schedule(self, schedule_id: UUID, owner_id: UUID) -> Schedule:
        schedule = await self.get_schedule(schedule_id)
        if schedule.owner_id != owner_id:
            raise ForbiddenError("You do not own this schedule")
        schedule.is_active = False
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def resume_schedule(self, schedule_id: UUID, owner_id: UUID) -> Schedule:
        schedule = await self.get_schedule(schedule_id)
        if schedule.owner_id != owner_id:
            raise ForbiddenError("You do not own this schedule")
        schedule.is_active = True
        schedule.consecutive_failures = 0
        schedule.next_run_at = compute_next_run(schedule.cron_expression, schedule.timezone)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    async def process_due_schedules(self) -> int:
        now = datetime.now(timezone.utc)

        stmt = (
            select(Schedule)
            .where(Schedule.is_active == True)  # noqa: E712
            .where(Schedule.next_run_at <= now)
            .where(
                or_(Schedule.max_runs == None, Schedule.run_count < Schedule.max_runs)  # noqa: E711
            )
            .where(Schedule.consecutive_failures < Schedule.max_consecutive_failures)
            .with_for_update(skip_locked=True)
            .limit(10)
        )
        result = await self.db.execute(stmt)
        schedules = list(result.scalars().all())

        processed = 0
        for schedule in schedules:
            try:
                await self._execute_schedule(schedule)
                schedule.consecutive_failures = 0
                processed += 1
            except Exception:
                logger.exception("Schedule %s execution failed", schedule.id)
                schedule.consecutive_failures += 1
                if schedule.consecutive_failures >= schedule.max_consecutive_failures:
                    schedule.is_active = False
                    logger.warning(
                        "Schedule %s auto-paused after %d consecutive failures",
                        schedule.id, schedule.consecutive_failures,
                    )

            schedule.last_run_at = now
            schedule.run_count += 1
            schedule.next_run_at = compute_next_run(
                schedule.cron_expression, schedule.timezone, after=now
            )

        await self.db.commit()

        if processed:
            logger.info("Processed %d/%d due schedules", processed, len(schedules))
        return processed

    async def _execute_schedule(self, schedule: Schedule) -> None:
        # Check credit minimum
        if schedule.credit_minimum > 0:
            from src.services.credit_ledger import CreditLedgerService
            ledger = CreditLedgerService(self.db)
            balance = await ledger.get_balance(schedule.owner_id)
            if balance < schedule.credit_minimum:
                raise MarketplaceError(
                    status_code=400,
                    detail=f"Balance ({balance}) below credit minimum ({schedule.credit_minimum})",
                )

        input_message = schedule.input_message or ""

        if schedule.schedule_type == "workflow" and schedule.target_id:
            from src.services.workflow_execution import WorkflowExecutionService
            engine = WorkflowExecutionService(self.db)
            await engine.execute_workflow(
                workflow_id=schedule.target_id,
                user_id=schedule.owner_id,
                input_message=input_message,
                schedule_id=schedule.id,
            )

        elif schedule.schedule_type == "crew" and schedule.target_id:
            from src.services.crew_service import CrewService
            from src.schemas.crew import CrewRunRequest
            crew_svc = CrewService(self.db)
            await crew_svc.run_crew(
                crew_id=schedule.target_id,
                owner_id=schedule.owner_id,
                data=CrewRunRequest(message=input_message),
            )

        elif schedule.schedule_type == "single_task" and schedule.task_params:
            from src.services.task_broker import TaskBrokerService
            from src.schemas.task import TaskCreate as TaskCreateSchema, TaskMessage, MessagePart

            params = schedule.task_params
            broker = TaskBrokerService(self.db)
            message = TaskMessage(
                role="user",
                parts=[MessagePart(type="text", content=input_message)],
            )
            task_data = TaskCreateSchema(
                provider_agent_id=params["provider_agent_id"],
                skill_id=params["skill_id"],
                messages=[message],
                confirmed=True,
            )
            await broker.create_task(data=task_data, user_id=schedule.owner_id)

        else:
            raise MarketplaceError(
                status_code=400,
                detail=f"Invalid schedule type or missing target: {schedule.schedule_type}",
            )
