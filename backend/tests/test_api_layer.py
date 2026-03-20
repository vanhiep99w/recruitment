"""Contract tests for the candidate/job API layer."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.routers.candidates as candidates_router
import app.routers.jobs as jobs_router
from app.auth import create_access_token
from app.database import get_db
from app.main import app
from app.models.candidate import Candidate
from app.models.candidate_profile import CandidateProfile
from app.models.job import Job
from app.models.pipeline import Pipeline
from app.models.talent_pool import TalentPool
from app.routers import pipelines as pipelines_router
from app.routers import talent_pools as talent_pools_router
from app.services.llm_client import get_llm_client
from app.services.match_engine import (
    calculate_skill_score,
    calculate_experience_score,
)
from app.services.search import build_candidate_embedding_text, years_of_experience


ORG_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


class DummyScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)


class DummyExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class DummySession:
    def __init__(self):
        self.added = []
        self.deleted = []
        self.scalar_queue = []
        self.scalars_queue = []
        self.execute_queue = []

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        now = datetime.now(timezone.utc)
        for item in self.added:
            if getattr(item, "id", None) is None and hasattr(item, "id"):
                item.id = uuid.uuid4()
            if getattr(item, "created_at", None) is None and hasattr(item, "created_at"):
                item.created_at = now
            if getattr(item, "updated_at", None) is None and hasattr(item, "updated_at"):
                item.updated_at = now

    async def refresh(self, item):
        await self.flush()

    async def scalar(self, _stmt):
        if self.scalar_queue:
            return self.scalar_queue.pop(0)
        return None

    async def scalars(self, _stmt):
        if self.scalars_queue:
            return DummyScalarResult(self.scalars_queue.pop(0))
        return DummyScalarResult([])

    async def execute(self, _stmt):
        if self.execute_queue:
            return DummyExecuteResult(self.execute_queue.pop(0))
        return DummyExecuteResult([])

    async def delete(self, item):
        self.deleted.append(item)


class DummyLLMClient:
    async def embed(self, _text):
        return [0.1, 0.2, 0.3]

    async def parse_jd(self, _text):
        return {
            "required_skills": ["Python", "FastAPI"],
            "nice_to_have_skills": ["PostgreSQL"],
            "seniority": "senior",
            "experience_years_min": 3,
            "experience_years_max": 6,
            "responsibilities": ["Build APIs"],
        }

    async def generate_match_rationale(self, **_kwargs):
        return "Strong API and database alignment."


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    token = create_access_token(user_id=USER_ID, org_id=ORG_ID)
    return {"Authorization": f"Bearer {token}"}


def override_dependencies(session: DummySession | None = None, llm_client: DummyLLMClient | None = None):
    db = session or DummySession()

    async def _get_db_override():
        yield db

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_llm_client] = lambda: llm_client or DummyLLMClient()
    return db


def test_candidates_requires_auth():
    override_dependencies()

    with TestClient(app) as client:
        response = client.get("/api/candidates")

    assert response.status_code == 401


def test_list_candidates_returns_paginated_payload(monkeypatch, auth_headers):
    override_dependencies()

    async def fake_list_candidates_for_org(*_args, **kwargs):
        assert kwargs["org_id"] == ORG_ID
        return {
            "data": [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Nguyen Van A",
                    "email": "a@example.com",
                    "phone": "0123456789",
                    "location": "Hanoi",
                    "parse_status": "parsed",
                    "skills": ["Python", "FastAPI"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
            "total": 1,
            "page": 1,
            "limit": 20,
        }

    monkeypatch.setattr(
        candidates_router,
        "list_candidates_for_org",
        fake_list_candidates_for_org,
    )

    with TestClient(app) as client:
        response = client.get("/api/candidates", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["data"][0]["name"] == "Nguyen Van A"


def test_create_job_from_json_returns_profile(auth_headers):
    session = override_dependencies()

    with TestClient(app) as client:
        response = client.post(
            "/api/jobs",
            headers=auth_headers,
            json={"title": "Senior Backend Engineer", "jd_text": "Need FastAPI and PostgreSQL"},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Senior Backend Engineer"
    assert payload["jd_profile"]["required_skills"] == ["Python", "FastAPI"]
    assert any(isinstance(item, Job) for item in session.added)


def test_get_candidate_returns_detail(monkeypatch, auth_headers):
    override_dependencies()
    candidate_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    sentinel = object()

    async def fake_get_candidate_detail_for_org(*_args, **_kwargs):
        return sentinel

    def fake_serialize_candidate_detail(_candidate):
        return {
            "id": str(candidate_id),
            "name": "Candidate A",
            "email": "a@example.com",
            "phone": "0123",
            "location": "Hanoi",
            "org_id": str(ORG_ID),
            "created_at": now.isoformat(),
            "profile": {
                "id": str(uuid.uuid4()),
                "candidate_id": str(candidate_id),
                "skills": ["Python"],
                "work_experience": [],
                "education": [],
                "languages": [],
                "certifications": [],
                "parse_status": "parsed",
                "parsed_at": now.isoformat(),
            },
            "cvs": [],
            "matches": [],
        }

    monkeypatch.setattr(candidates_router, "get_candidate_detail_for_org", fake_get_candidate_detail_for_org)
    monkeypatch.setattr(candidates_router, "serialize_candidate_detail", fake_serialize_candidate_detail)

    with TestClient(app) as client:
        response = client.get(f"/api/candidates/{candidate_id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Candidate A"


def test_update_candidate_profile_marks_manual_review(monkeypatch, auth_headers):
    session = override_dependencies()
    candidate_id = uuid.uuid4()
    profile = CandidateProfile(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        skills=["Python"],
        work_experience=[],
    )
    candidate = Candidate(
        id=candidate_id,
        name="Candidate A",
        email="a@example.com",
        phone="0123",
        location="Hanoi",
        org_id=ORG_ID,
    )
    candidate.profile = profile

    async def fake_get_candidate_detail_for_org(*_args, **_kwargs):
        return candidate

    monkeypatch.setattr(candidates_router, "get_candidate_detail_for_org", fake_get_candidate_detail_for_org)

    with TestClient(app) as client:
        response = client.patch(
            f"/api/candidates/{candidate_id}/profile",
            headers=auth_headers,
            json={
                "skills": ["Python", "FastAPI"],
                "work_experience": [{"years": 4}],
                "education": [{"degree": "Bachelor"}],
                "languages": ["vi", "en"],
                "certifications": ["AWS"],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["parse_status"] == "manually_reviewed"
    assert payload["skills"] == ["Python", "FastAPI"]
    assert any(isinstance(item, CandidateProfile) for item in session.added) is False


def test_review_candidate_profile_returns_duplicate(monkeypatch, auth_headers):
    override_dependencies()
    candidate_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    candidate = Candidate(
        id=candidate_id,
        name="Candidate A",
        email="a@example.com",
        phone="0123",
        location="Hanoi",
        org_id=ORG_ID,
    )

    async def fake_update_candidate_profile(**_kwargs):
        return None

    async def fake_get_candidate_detail_for_org(*_args, **_kwargs):
        return candidate

    def fake_serialize_candidate_detail(_candidate):
        return {
            "id": str(candidate_id),
            "name": "Candidate A",
            "email": "a@example.com",
            "phone": "0123",
            "location": "Hanoi",
            "org_id": str(ORG_ID),
            "created_at": now.isoformat(),
            "profile": None,
            "cvs": [],
            "matches": [],
        }

    async def fake_find_duplicate_candidate(*_args, **_kwargs):
        return {
            "duplicate": True,
            "existing_id": uuid.uuid4(),
            "existing_name": "Candidate B",
        }

    monkeypatch.setattr(candidates_router, "update_candidate_profile", fake_update_candidate_profile)
    monkeypatch.setattr(candidates_router, "get_candidate_detail_for_org", fake_get_candidate_detail_for_org)
    monkeypatch.setattr(candidates_router, "serialize_candidate_detail", fake_serialize_candidate_detail)
    monkeypatch.setattr(candidates_router, "find_duplicate_candidate", fake_find_duplicate_candidate)

    with TestClient(app) as client:
        response = client.post(
            f"/api/candidates/{candidate_id}/review",
            headers=auth_headers,
            json={"name": "Candidate A", "skills": ["Python"]},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["duplicate"]["duplicate"] is True
    assert payload["candidate"]["name"] == "Candidate A"


def test_create_job_from_docx_upload(monkeypatch, auth_headers):
    override_dependencies()

    async def fake_extract_uploaded_text(_upload):
        return "Need FastAPI and PostgreSQL"

    monkeypatch.setattr(jobs_router, "_extract_uploaded_text", fake_extract_uploaded_text)

    with TestClient(app) as client:
        response = client.post(
            "/api/jobs",
            headers=auth_headers,
            data={"title": "Platform Engineer"},
            files={
                "jd_file": (
                    "role.docx",
                    b"placeholder",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 201
    assert response.json()["title"] == "Platform Engineer"


def test_trigger_job_match_maps_service_results(monkeypatch, auth_headers):
    override_dependencies()

    match_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    async def fake_score_candidates_for_job(*_args, **_kwargs):
        return [
            SimpleNamespace(
                id=match_id,
                candidate_id=candidate_id,
                overall_score=88,
                skill_score=90,
                experience_score=85,
                education_score=80,
                rationale="Strong API and database alignment.",
            )
        ]

    monkeypatch.setattr(jobs_router, "score_candidates_for_job", fake_score_candidates_for_job)

    with TestClient(app) as client:
        response = client.post(f"/api/jobs/{uuid.uuid4()}/match", headers=auth_headers, json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["match_id"] == str(match_id)
    assert payload[0]["overall_score"] == 88


def test_update_pipeline_stage_creates_record(auth_headers):
    session = override_dependencies()
    candidate = Candidate(name="Candidate A", org_id=ORG_ID)
    job = Job(title="Job A", org_id=ORG_ID)
    session.scalar_queue = [candidate, job, None]

    with TestClient(app) as client:
        response = client.patch(
            f"/api/pipelines/{uuid.uuid4()}/{uuid.uuid4()}",
            headers=auth_headers,
            json={"stage": "shortlisted"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stage"] == "shortlisted"
    assert any(isinstance(item, Pipeline) for item in session.added)


def test_create_talent_pool_uses_auth_org(auth_headers):
    session = override_dependencies()

    with TestClient(app) as client:
        response = client.post("/api/talent-pools", headers=auth_headers, json={"name": "Top Talent"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Top Talent"
    assert any(isinstance(item, TalentPool) and item.org_id == ORG_ID for item in session.added)


def test_add_pool_members_returns_added_count(auth_headers):
    session = override_dependencies()
    pool_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    session.scalar_queue = [TalentPool(id=pool_id, name="Pool", org_id=ORG_ID)]
    session.scalars_queue = [[Candidate(id=candidate_id, name="Candidate", org_id=ORG_ID)]]
    session.execute_queue = [[]]

    with TestClient(app) as client:
        response = client.post(
            f"/api/talent-pools/{pool_id}/members",
            headers=auth_headers,
            json={"candidate_ids": [str(candidate_id)]},
        )

    assert response.status_code == 200
    assert response.json() == {"added": 1}


def test_years_of_experience_uses_explicit_years_and_dates():
    experience = [
        {"years": 2},
        {"start": "2020-01-01", "end": "2021-01-01"},
    ]
    assert years_of_experience(experience) >= 3.0


def test_build_candidate_embedding_text_contains_name_skills_and_roles():
    text = build_candidate_embedding_text(
        name="Nguyen Van A",
        skills=["Python", "FastAPI"],
        work_experience=[{"title": "Backend Engineer", "company": "Acme"}],
    )
    assert "Nguyen Van A" in text
    assert "Python, FastAPI" in text
    assert "Backend Engineer" in text


def test_match_scoring_helpers_cover_required_and_optional_skills():
    assert calculate_skill_score(["Python", "SQL"], ["Python"], ["SQL"]) == 100
    assert calculate_experience_score(candidate_years=1, minimum_years=3, maximum_years=5) < 100
