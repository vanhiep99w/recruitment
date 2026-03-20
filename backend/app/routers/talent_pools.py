"""Talent pool API routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, require_auth_context
from app.database import get_db
from app.models.candidate import Candidate
from app.models.talent_pool import TalentPool
from app.models.talent_pool_member import TalentPoolMember
from app.schemas.talent_pool import (
    TalentPoolCreateRequest,
    TalentPoolListResponse,
    TalentPoolMemberBatchAdd,
    TalentPoolRead,
)
from app.services.search import list_talent_pools_for_org

router = APIRouter(prefix="/talent-pools", tags=["talent-pools"])


@router.get("", response_model=TalentPoolListResponse)
async def list_talent_pools(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
) -> TalentPoolListResponse:
    return TalentPoolListResponse.model_validate(
        {"data": await list_talent_pools_for_org(db, org_id=auth.org_id)}
    )


@router.post("", response_model=TalentPoolRead, status_code=status.HTTP_201_CREATED)
async def create_talent_pool(
    payload: TalentPoolCreateRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
) -> TalentPoolRead:
    pool = TalentPool(name=payload.name, org_id=auth.org_id)
    db.add(pool)
    await db.flush()
    await db.refresh(pool)
    return TalentPoolRead.model_validate(pool)


@router.post("/{pool_id}/members", response_model=dict[str, int])
async def add_pool_members(
    pool_id: uuid.UUID,
    payload: TalentPoolMemberBatchAdd,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
) -> dict[str, int]:
    pool = await db.scalar(select(TalentPool).where(TalentPool.id == pool_id, TalentPool.org_id == auth.org_id))
    if pool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Talent pool not found")

    candidates = list(
        (
            await db.scalars(
                select(Candidate).where(
                    Candidate.org_id == auth.org_id,
                    Candidate.id.in_(payload.candidate_ids),
                )
            )
        ).all()
    )
    if len(candidates) != len(set(payload.candidate_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more candidates not found")

    existing_ids = {
        candidate_id
        for candidate_id, in (
            await db.execute(
                select(TalentPoolMember.candidate_id).where(TalentPoolMember.pool_id == pool_id)
            )
        ).all()
    }
    added = 0
    for candidate_id in payload.candidate_ids:
        if candidate_id in existing_ids:
            continue
        db.add(TalentPoolMember(pool_id=pool_id, candidate_id=candidate_id))
        added += 1
    await db.flush()
    return {"added": added}


@router.delete("/{pool_id}/members/{candidate_id}", response_model=dict[str, bool])
async def remove_pool_member(
    pool_id: uuid.UUID,
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
) -> dict[str, bool]:
    pool = await db.scalar(select(TalentPool).where(TalentPool.id == pool_id, TalentPool.org_id == auth.org_id))
    if pool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Talent pool not found")

    membership = await db.scalar(
        select(TalentPoolMember).where(
            TalentPoolMember.pool_id == pool_id,
            TalentPoolMember.candidate_id == candidate_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool member not found")

    await db.delete(membership)
    await db.flush()
    return {"removed": True}
