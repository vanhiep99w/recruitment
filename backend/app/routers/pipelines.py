"""Pipeline API routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, require_auth_context
from app.database import get_db
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.pipeline import Pipeline
from app.schemas.match import PipelineRead, PipelineUpdate

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.patch("/{candidate_id}/{job_id}", response_model=PipelineRead)
async def update_pipeline_stage(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    payload: PipelineUpdate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
) -> PipelineRead:
    candidate = await db.scalar(
        select(Candidate).where(Candidate.id == candidate_id, Candidate.org_id == auth.org_id)
    )
    job = await db.scalar(select(Job).where(Job.id == job_id, Job.org_id == auth.org_id))
    if candidate is None or job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate or job not found")

    pipeline = await db.scalar(
        select(Pipeline).where(Pipeline.candidate_id == candidate_id, Pipeline.job_id == job_id)
    )
    if pipeline is None:
        pipeline = Pipeline(candidate_id=candidate_id, job_id=job_id, stage=payload.stage)
        db.add(pipeline)
    else:
        pipeline.stage = payload.stage

    await db.flush()
    await db.refresh(pipeline)
    return PipelineRead.model_validate(pipeline)
