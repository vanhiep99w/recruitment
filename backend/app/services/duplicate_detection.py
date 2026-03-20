"""Duplicate candidate detection helpers."""

from __future__ import annotations

import re
import unicodedata
import uuid
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate


def normalize_name(value: str | None) -> str:
    """Normalize names for fuzzy duplicate checks."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = without_marks.lower()
    collapsed = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(collapsed.split())


def similarity_score(left: str | None, right: str | None) -> float:
    """Return a 0-1 similarity score for two names."""
    left_normalized = normalize_name(left)
    right_normalized = normalize_name(right)
    if not left_normalized or not right_normalized:
        return 0.0
    return SequenceMatcher(None, left_normalized, right_normalized).ratio()


async def find_duplicate_candidate(
    session: AsyncSession,
    org_id: uuid.UUID,
    name: str | None,
    email: str | None,
    threshold: float = 0.85,
) -> Candidate | None:
    """Find a duplicate candidate in the same org via exact email or similar name."""
    candidates_stmt = select(Candidate).where(Candidate.org_id == org_id)

    normalized_email = (email or "").strip().lower()
    if normalized_email:
        email_result = await session.execute(candidates_stmt)
        for candidate in email_result.scalars().all():
            if (candidate.email or "").strip().lower() == normalized_email:
                return candidate

    normalized_name = normalize_name(name)
    if not normalized_name:
        return None

    name_result = await session.execute(candidates_stmt)
    best_match = None
    best_score = 0.0
    for candidate in name_result.scalars().all():
        score = similarity_score(candidate.name, normalized_name)
        if score >= threshold and score > best_score:
            best_match = candidate
            best_score = score

    return best_match
