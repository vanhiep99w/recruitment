"""Tests for duplicate candidate detection helpers."""

import uuid
from types import SimpleNamespace

import pytest


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)


class _ExecuteResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _ScalarResult(self._items)


class _FakeSession:
    def __init__(self, email_matches=None, name_matches=None):
        self.email_matches = email_matches or []
        self.name_matches = name_matches or []
        self.calls = 0

    async def execute(self, _statement):
        self.calls += 1
        if self.calls == 1 and self.email_matches:
            return _ExecuteResult(self.email_matches)
        return _ExecuteResult(self.name_matches)


@pytest.mark.asyncio
async def test_find_duplicate_candidate_prefers_exact_email_match():
    """Exact email match in the same org should be returned as duplicate."""
    from app.services.duplicate_detection import find_duplicate_candidate

    existing = SimpleNamespace(id=uuid.uuid4(), email="dup@example.com", name="Nguyen Van A")
    session = _FakeSession(email_matches=[existing])

    result = await find_duplicate_candidate(
        session=session,
        org_id=uuid.uuid4(),
        name="Another Name",
        email="dup@example.com",
    )

    assert result is existing


@pytest.mark.asyncio
async def test_find_duplicate_candidate_uses_name_similarity_when_email_missing():
    """Similar normalized names should count as duplicates without email."""
    from app.services.duplicate_detection import find_duplicate_candidate

    existing = SimpleNamespace(id=uuid.uuid4(), email=None, name="Nguyen Van A")
    session = _FakeSession(email_matches=[], name_matches=[existing])

    result = await find_duplicate_candidate(
        session=session,
        org_id=uuid.uuid4(),
        name="Nguyễn Văn A",
        email=None,
    )

    assert result is existing


@pytest.mark.asyncio
async def test_find_duplicate_candidate_returns_none_for_distinct_candidate():
    """Unrelated candidates should not be flagged as duplicates."""
    from app.services.duplicate_detection import find_duplicate_candidate

    existing = SimpleNamespace(id=uuid.uuid4(), email="other@example.com", name="Tran Thi B")
    session = _FakeSession(email_matches=[], name_matches=[existing])

    result = await find_duplicate_candidate(
        session=session,
        org_id=uuid.uuid4(),
        name="Le Van C",
        email="new@example.com",
    )

    assert result is None
