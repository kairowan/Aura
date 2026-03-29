"""Gateway router for automation job management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.automation.service import (
    AutomationJob,
    AutomationJobCreate,
    AutomationJobUpdate,
    get_automation_service,
    start_automation_service,
)

router = APIRouter(prefix="/api/automations", tags=["automations"])


class AutomationListResponse(BaseModel):
    jobs: list[AutomationJob] = Field(default_factory=list)


async def _require_service():
    service = get_automation_service()
    if service is None:
        service = await start_automation_service()
    return service


@router.get("/", response_model=AutomationListResponse)
async def list_automation_jobs() -> AutomationListResponse:
    service = await _require_service()
    return AutomationListResponse(jobs=service.list_jobs())


@router.post("/", response_model=AutomationJob)
async def create_automation_job(payload: AutomationJobCreate) -> AutomationJob:
    service = await _require_service()
    return await service.create_job(payload)


@router.patch("/{job_id}", response_model=AutomationJob)
async def update_automation_job(job_id: str, payload: AutomationJobUpdate) -> AutomationJob:
    service = await _require_service()
    try:
        return await service.update_job(job_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Automation job not found") from exc


@router.delete("/{job_id}")
async def delete_automation_job(job_id: str) -> dict[str, bool]:
    service = await _require_service()
    deleted = await service.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Automation job not found")
    return {"success": True}


@router.post("/{job_id}/run", response_model=AutomationJob)
async def run_automation_job(job_id: str) -> AutomationJob:
    service = await _require_service()
    try:
        return await service.run_now(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Automation job not found") from exc
