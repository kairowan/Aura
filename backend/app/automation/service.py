"""Automation service for scheduled Aura jobs."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from app.channels.manager import DEFAULT_ASSISTANT_ID, DEFAULT_RUN_CONFIG, DEFAULT_RUN_CONTEXT, _extract_response_text
from app.channels.message_bus import OutboundMessage
from aura.config.paths import get_paths

logger = logging.getLogger(__name__)

DEFAULT_LANGGRAPH_URL = "http://localhost:2024"
POLL_INTERVAL_SECONDS = 15


class AutomationJob(BaseModel):
    id: str
    name: str
    prompt: str
    schedule_type: Literal["interval", "daily"] = "interval"
    interval_minutes: int = Field(default=60, ge=1)
    daily_time: str = "09:00"
    assistant_id: str = DEFAULT_ASSISTANT_ID
    enabled: bool = True
    delivery_channel: str | None = None
    delivery_chat_id: str | None = None
    created_at: float
    updated_at: float
    next_run_at: float | None = None
    last_run_at: float | None = None
    last_status: Literal["idle", "running", "success", "error"] = "idle"
    last_error: str | None = None
    last_output: str | None = None
    last_thread_id: str | None = None

    @field_validator("daily_time")
    @classmethod
    def validate_daily_time(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%H:%M")
        except ValueError as exc:
            raise ValueError("daily_time must use HH:MM format") from exc
        return value


class AutomationJobCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    prompt: str = Field(..., min_length=1, max_length=8000)
    schedule_type: Literal["interval", "daily"] = "interval"
    interval_minutes: int = Field(default=60, ge=1)
    daily_time: str = "09:00"
    assistant_id: str | None = None
    enabled: bool = True
    delivery_channel: str | None = None
    delivery_chat_id: str | None = None

    @field_validator("daily_time")
    @classmethod
    def validate_daily_time(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%H:%M")
        except ValueError as exc:
            raise ValueError("daily_time must use HH:MM format") from exc
        return value


class AutomationJobUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    prompt: str | None = Field(default=None, min_length=1, max_length=8000)
    schedule_type: Literal["interval", "daily"] | None = None
    interval_minutes: int | None = Field(default=None, ge=1)
    daily_time: str | None = None
    assistant_id: str | None = None
    enabled: bool | None = None
    delivery_channel: str | None = None
    delivery_chat_id: str | None = None

    @field_validator("daily_time")
    @classmethod
    def validate_daily_time(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            datetime.strptime(value, "%H:%M")
        except ValueError as exc:
            raise ValueError("daily_time must use HH:MM format") from exc
        return value


class AutomationStore:
    """Simple JSON store for automation jobs."""

    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            path = Path(get_paths().base_dir) / "automations" / "jobs.json"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, AutomationJob]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Corrupt automation store at %s, starting fresh", self.path)
            return {}

        jobs: dict[str, AutomationJob] = {}
        if isinstance(data, list):
            for item in data:
                try:
                    job = AutomationJob.model_validate(item)
                except Exception:
                    logger.warning("Skipping invalid automation job entry: %s", item)
                    continue
                jobs[job.id] = job
        return jobs

    def save(self, jobs: dict[str, AutomationJob]) -> None:
        payload = [job.model_dump() for job in jobs.values()]
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


class AutomationService:
    """Runs scheduled Aura prompts against LangGraph and persists results."""

    def __init__(
        self,
        *,
        store: AutomationStore | None = None,
        langgraph_url: str = DEFAULT_LANGGRAPH_URL,
        poll_interval_seconds: int = POLL_INTERVAL_SECONDS,
    ) -> None:
        self._store = store or AutomationStore()
        self._jobs = self._store.load()
        self._langgraph_url = langgraph_url
        self._poll_interval_seconds = poll_interval_seconds
        self._client = None
        self._lock = asyncio.Lock()
        self._loop_task: asyncio.Task | None = None
        self._running = False
        self._active_runs: dict[str, asyncio.Task] = {}

    def list_jobs(self) -> list[AutomationJob]:
        return sorted(
            (job.model_copy(deep=True) for job in self._jobs.values()),
            key=lambda job: (job.next_run_at or float("inf"), job.name.lower()),
        )

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        async with self._lock:
            changed = False
            for job in self._jobs.values():
                desired_next = self._compute_next_run(job, from_ts=time.time()) if job.enabled else None
                if job.next_run_at is None and desired_next is not None:
                    job.next_run_at = desired_next
                    changed = True
            if changed:
                self._persist()
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("AutomationService started with %d job(s)", len(self._jobs))

    async def stop(self) -> None:
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None

        running_tasks = list(self._active_runs.values())
        for task in running_tasks:
            task.cancel()
        if running_tasks:
            await asyncio.gather(*running_tasks, return_exceptions=True)
        self._active_runs.clear()
        logger.info("AutomationService stopped")

    async def create_job(self, payload: AutomationJobCreate) -> AutomationJob:
        now = time.time()
        job = AutomationJob(
            id=uuid4().hex[:12],
            name=payload.name.strip(),
            prompt=payload.prompt.strip(),
            schedule_type=payload.schedule_type,
            interval_minutes=payload.interval_minutes,
            daily_time=payload.daily_time,
            assistant_id=(payload.assistant_id or DEFAULT_ASSISTANT_ID).strip() or DEFAULT_ASSISTANT_ID,
            enabled=payload.enabled,
            delivery_channel=(payload.delivery_channel or None),
            delivery_chat_id=(payload.delivery_chat_id or None),
            created_at=now,
            updated_at=now,
            next_run_at=None,
        )
        if job.enabled:
            job.next_run_at = self._compute_next_run(job, from_ts=now)

        async with self._lock:
            self._jobs[job.id] = job
            self._persist()
        return job.model_copy(deep=True)

    async def update_job(self, job_id: str, payload: AutomationJobUpdate) -> AutomationJob:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)

            update_data = payload.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if key == "assistant_id" and value is not None:
                    value = value.strip() or DEFAULT_ASSISTANT_ID
                if key in {"delivery_channel", "delivery_chat_id"} and value == "":
                    value = None
                setattr(job, key, value)

            job.updated_at = time.time()
            if not job.assistant_id:
                job.assistant_id = DEFAULT_ASSISTANT_ID
            job.next_run_at = self._compute_next_run(job, from_ts=time.time()) if job.enabled else None
            self._persist()
            return job.model_copy(deep=True)

    async def delete_job(self, job_id: str) -> bool:
        async with self._lock:
            removed = self._jobs.pop(job_id, None)
            self._persist()

        task = self._active_runs.pop(job_id, None)
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        return removed is not None

    async def run_now(self, job_id: str) -> AutomationJob:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)

            task = self._active_runs.get(job_id)
            if task and not task.done():
                return job.model_copy(deep=True)

            job.last_status = "running"
            job.last_error = None
            job.updated_at = time.time()
            self._persist()
            run_task = asyncio.create_task(self._execute_job(job_id))
            self._active_runs[job_id] = run_task
            run_task.add_done_callback(lambda finished, current_id=job_id: self._active_runs.pop(current_id, None))
            return job.model_copy(deep=True)

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self._dispatch_due_jobs()
                await asyncio.sleep(self._poll_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("AutomationService loop error")
                await asyncio.sleep(self._poll_interval_seconds)

    async def _dispatch_due_jobs(self) -> None:
        now = time.time()
        due_job_ids: list[str] = []
        async with self._lock:
            for job in self._jobs.values():
                if not job.enabled or job.next_run_at is None:
                    continue
                if job.id in self._active_runs:
                    continue
                if job.next_run_at <= now:
                    due_job_ids.append(job.id)

        for job_id in due_job_ids:
            task = asyncio.create_task(self._execute_job(job_id))
            self._active_runs[job_id] = task
            task.add_done_callback(lambda finished, current_id=job_id: self._active_runs.pop(current_id, None))

    async def _execute_job(self, job_id: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.last_status = "running"
            job.last_error = None
            job.updated_at = time.time()
            self._persist()
            job_snapshot = job.model_copy(deep=True)

        try:
            client = self._get_client()
            thread = await client.threads.create()
            thread_id = thread["thread_id"]
            result = await client.runs.wait(
                thread_id,
                job_snapshot.assistant_id,
                input={"messages": [{"role": "human", "content": job_snapshot.prompt}]},
                config=DEFAULT_RUN_CONFIG,
                context={
                    **DEFAULT_RUN_CONTEXT,
                    "thread_id": thread_id,
                    "automation": {
                        "job_id": job_snapshot.id,
                        "job_name": job_snapshot.name,
                    },
                },
            )
            output_text = _extract_response_text(result) or "(Automation completed without text output)"
            await self._finalize_success(job_snapshot.id, thread_id, output_text)
            await self._deliver_result(job_snapshot, thread_id, output_text)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Automation job %s failed", job_id)
            await self._finalize_error(job_id, str(exc))

    async def _finalize_success(self, job_id: str, thread_id: str, output_text: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            now = time.time()
            job.last_status = "success"
            job.last_run_at = now
            job.updated_at = now
            job.last_error = None
            job.last_output = output_text[:4000]
            job.last_thread_id = thread_id
            job.next_run_at = self._compute_next_run(job, from_ts=now) if job.enabled else None
            self._persist()

    async def _finalize_error(self, job_id: str, error_text: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            now = time.time()
            job.last_status = "error"
            job.last_run_at = now
            job.updated_at = now
            job.last_error = error_text[:1000]
            job.next_run_at = self._compute_next_run(job, from_ts=now) if job.enabled else None
            self._persist()

    async def _deliver_result(self, job: AutomationJob, thread_id: str, output_text: str) -> None:
        if not job.delivery_channel or not job.delivery_chat_id:
            return

        try:
            from app.channels.service import get_channel_service

            channel_service = get_channel_service()
            if channel_service is None:
                logger.warning("Automation delivery skipped because channel service is not running")
                return

            await channel_service.bus.publish_outbound(
                OutboundMessage(
                    channel_name=job.delivery_channel,
                    chat_id=job.delivery_chat_id,
                    thread_id=thread_id,
                    text=output_text,
                    metadata={"automation_job_id": job.id},
                )
            )
        except Exception:
            logger.exception("Failed to deliver automation result for job %s", job.id)

    def _persist(self) -> None:
        self._store.save(self._jobs)

    def _get_client(self):
        if self._client is None:
            from langgraph_sdk import get_client

            self._client = get_client(url=self._langgraph_url)
        return self._client

    @staticmethod
    def _compute_next_run(job: AutomationJob, *, from_ts: float) -> float:
        if job.schedule_type == "interval":
            return from_ts + max(job.interval_minutes, 1) * 60

        local_now = datetime.fromtimestamp(from_ts).astimezone()
        hour, minute = [int(part) for part in job.daily_time.split(":", 1)]
        candidate = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= local_now:
            candidate += timedelta(days=1)
        return candidate.timestamp()


_automation_service: AutomationService | None = None


def get_automation_service() -> AutomationService | None:
    return _automation_service


async def start_automation_service() -> AutomationService:
    global _automation_service
    if _automation_service is not None:
        return _automation_service
    _automation_service = AutomationService()
    await _automation_service.start()
    return _automation_service


async def stop_automation_service() -> None:
    global _automation_service
    if _automation_service is not None:
        await _automation_service.stop()
        _automation_service = None
