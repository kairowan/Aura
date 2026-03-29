from __future__ import annotations

import asyncio
from pathlib import Path

from app.automation.service import AutomationJobCreate, AutomationJobUpdate, AutomationService, AutomationStore


def test_create_interval_job_persists_next_run(tmp_path: Path):
    service = AutomationService(
        store=AutomationStore(tmp_path / "jobs.json"),
        poll_interval_seconds=3600,
    )

    async def run():
        job = await service.create_job(
            AutomationJobCreate(
                name="daily-brief",
                prompt="Summarize the latest product updates.",
                schedule_type="interval",
                interval_minutes=30,
            )
        )
        assert job.interval_minutes == 30
        assert job.next_run_at is not None
        assert job.next_run_at > job.updated_at
        assert len(service.list_jobs()) == 1

    asyncio.run(run())


def test_update_job_switches_to_daily_schedule(tmp_path: Path):
    service = AutomationService(
        store=AutomationStore(tmp_path / "jobs.json"),
        poll_interval_seconds=3600,
    )

    async def run():
        created = await service.create_job(
            AutomationJobCreate(
                name="market-scan",
                prompt="Check competitor announcements.",
                schedule_type="interval",
                interval_minutes=45,
            )
        )
        updated = await service.update_job(
            created.id,
            AutomationJobUpdate(
                schedule_type="daily",
                daily_time="08:30",
                enabled=True,
            ),
        )

        assert updated.schedule_type == "daily"
        assert updated.daily_time == "08:30"
        assert updated.next_run_at is not None
        assert updated.next_run_at > updated.updated_at

    asyncio.run(run())
