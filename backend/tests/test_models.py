"""
Tests for SQLAlchemy models — verifies all tables and required columns exist.
Phase 1: RED — these tests must fail before implementation.
"""
import pytest
import inspect


def test_organization_model_exists():
    """Organization model must be importable."""
    from app.models.organization import Organization
    assert Organization is not None


def test_organization_model_columns():
    """Organization model must have required columns."""
    from app.models.organization import Organization
    columns = {c.name for c in Organization.__table__.columns}
    assert "id" in columns
    assert "name" in columns
    assert "plan_tier" in columns
    assert "seats" in columns
    assert "created_at" in columns


def test_user_model_exists():
    """User model must be importable."""
    from app.models.user import User
    assert User is not None


def test_user_model_columns():
    """User model must have required columns."""
    from app.models.user import User
    columns = {c.name for c in User.__table__.columns}
    assert "id" in columns
    assert "name" in columns
    assert "email" in columns
    assert "role" in columns
    assert "org_id" in columns
    assert "created_at" in columns


def test_candidate_model_exists():
    """Candidate model must be importable."""
    from app.models.candidate import Candidate
    assert Candidate is not None


def test_candidate_model_columns():
    """Candidate model must have required columns."""
    from app.models.candidate import Candidate
    columns = {c.name for c in Candidate.__table__.columns}
    assert "id" in columns
    assert "name" in columns
    assert "email" in columns
    assert "phone" in columns
    assert "location" in columns
    assert "org_id" in columns
    assert "created_at" in columns


def test_candidate_profile_model_exists():
    """CandidateProfile model must be importable."""
    from app.models.candidate_profile import CandidateProfile
    assert CandidateProfile is not None


def test_candidate_profile_model_columns():
    """CandidateProfile model must have required columns including vector."""
    from app.models.candidate_profile import CandidateProfile
    columns = {c.name for c in CandidateProfile.__table__.columns}
    assert "id" in columns
    assert "candidate_id" in columns
    assert "skills" in columns
    assert "work_experience" in columns
    assert "education" in columns
    assert "languages" in columns
    assert "certifications" in columns
    assert "embedding" in columns
    assert "parse_status" in columns
    assert "parsed_at" in columns


def test_candidate_profile_embedding_is_vector():
    """CandidateProfile.embedding must be a pgvector Vector column."""
    from app.models.candidate_profile import CandidateProfile
    from pgvector.sqlalchemy import Vector
    embedding_col = CandidateProfile.__table__.columns["embedding"]
    assert isinstance(embedding_col.type, Vector)


def test_cv_model_exists():
    """CV model must be importable."""
    from app.models.cv import CV
    assert CV is not None


def test_cv_model_columns():
    """CV model must have required columns."""
    from app.models.cv import CV
    columns = {c.name for c in CV.__table__.columns}
    assert "id" in columns
    assert "candidate_id" in columns
    assert "file_url" in columns
    assert "file_type" in columns
    assert "upload_ts" in columns
    assert "parse_status" in columns
    assert "raw_text" in columns


def test_job_model_exists():
    """Job model must be importable."""
    from app.models.job import Job
    assert Job is not None


def test_job_model_columns():
    """Job model must have required columns."""
    from app.models.job import Job
    columns = {c.name for c in Job.__table__.columns}
    assert "id" in columns
    assert "title" in columns
    assert "org_id" in columns
    assert "jd_text" in columns
    assert "status" in columns
    assert "created_at" in columns


def test_jd_profile_model_exists():
    """JDProfile model must be importable."""
    from app.models.jd_profile import JDProfile
    assert JDProfile is not None


def test_jd_profile_model_columns():
    """JDProfile model must have required columns including vector."""
    from app.models.jd_profile import JDProfile
    columns = {c.name for c in JDProfile.__table__.columns}
    assert "id" in columns
    assert "job_id" in columns
    assert "required_skills" in columns
    assert "nice_to_have_skills" in columns
    assert "seniority" in columns
    assert "experience_years_min" in columns
    assert "experience_years_max" in columns
    assert "responsibilities" in columns
    assert "embedding" in columns


def test_jd_profile_embedding_is_vector():
    """JDProfile.embedding must be a pgvector Vector column."""
    from app.models.jd_profile import JDProfile
    from pgvector.sqlalchemy import Vector
    embedding_col = JDProfile.__table__.columns["embedding"]
    assert isinstance(embedding_col.type, Vector)


def test_match_model_exists():
    """Match model must be importable."""
    from app.models.match import Match
    assert Match is not None


def test_match_model_columns():
    """Match model must have required columns."""
    from app.models.match import Match
    columns = {c.name for c in Match.__table__.columns}
    assert "id" in columns
    assert "candidate_id" in columns
    assert "job_id" in columns
    assert "overall_score" in columns
    assert "skill_score" in columns
    assert "experience_score" in columns
    assert "education_score" in columns
    assert "rationale" in columns
    assert "created_at" in columns


def test_pipeline_model_exists():
    """Pipeline model must be importable."""
    from app.models.pipeline import Pipeline
    assert Pipeline is not None


def test_pipeline_model_columns():
    """Pipeline model must have required columns."""
    from app.models.pipeline import Pipeline
    columns = {c.name for c in Pipeline.__table__.columns}
    assert "id" in columns
    assert "job_id" in columns
    assert "candidate_id" in columns
    assert "stage" in columns
    assert "updated_at" in columns


def test_talent_pool_model_exists():
    """TalentPool model must be importable."""
    from app.models.talent_pool import TalentPool
    assert TalentPool is not None


def test_talent_pool_model_columns():
    """TalentPool model must have required columns."""
    from app.models.talent_pool import TalentPool
    columns = {c.name for c in TalentPool.__table__.columns}
    assert "id" in columns
    assert "name" in columns
    assert "org_id" in columns
    assert "created_at" in columns


def test_talent_pool_member_model_exists():
    """TalentPoolMember model must be importable."""
    from app.models.talent_pool_member import TalentPoolMember
    assert TalentPoolMember is not None


def test_talent_pool_member_model_columns():
    """TalentPoolMember model must have required columns."""
    from app.models.talent_pool_member import TalentPoolMember
    columns = {c.name for c in TalentPoolMember.__table__.columns}
    assert "pool_id" in columns
    assert "candidate_id" in columns


def test_all_models_importable_from_package():
    """All models must be importable from app.models package."""
    from app.models import (
        Organization,
        User,
        Candidate,
        CandidateProfile,
        CV,
        Job,
        JDProfile,
        Match,
        Pipeline,
        TalentPool,
        TalentPoolMember,
    )
    models = [Organization, User, Candidate, CandidateProfile, CV, Job,
              JDProfile, Match, Pipeline, TalentPool, TalentPoolMember]
    assert all(m is not None for m in models)
