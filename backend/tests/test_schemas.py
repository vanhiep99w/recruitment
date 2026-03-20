"""
Tests for Pydantic v2 schemas — validates instantiation, field validation,
defaults, and type coercion.
"""
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Common schemas
# ---------------------------------------------------------------------------
class TestBaseSchema:
    def test_base_schema_importable(self):
        from app.schemas.common import BaseSchema
        assert BaseSchema is not None

    def test_uuid_mixin(self):
        from app.schemas.common import UUIDMixin
        uid = uuid.uuid4()
        obj = UUIDMixin(id=uid)
        assert obj.id == uid

    def test_uuid_mixin_missing_id_raises(self):
        from app.schemas.common import UUIDMixin
        with pytest.raises(ValidationError):
            UUIDMixin()

    def test_timestamp_mixin(self):
        from app.schemas.common import TimestampMixin
        now = datetime.now(timezone.utc)
        obj = TimestampMixin(created_at=now)
        assert obj.created_at == now

    def test_timestamp_mixin_missing_raises(self):
        from app.schemas.common import TimestampMixin
        with pytest.raises(ValidationError):
            TimestampMixin()


# ---------------------------------------------------------------------------
# Organization schemas
# ---------------------------------------------------------------------------
class TestOrganizationSchemas:
    def test_organization_create_valid(self):
        from app.schemas.organization import OrganizationCreate
        org = OrganizationCreate(name="Acme Corp", org_id_not_needed=None)
        assert org.name == "Acme Corp"

    def test_organization_create_defaults(self):
        from app.schemas.organization import OrganizationCreate
        org = OrganizationCreate(name="Acme")
        assert org.plan_tier == "free"
        assert org.seats == 5

    def test_organization_create_custom_plan(self):
        from app.schemas.organization import OrganizationCreate
        org = OrganizationCreate(name="BigCo", plan_tier="enterprise", seats=100)
        assert org.plan_tier == "enterprise"
        assert org.seats == 100

    def test_organization_create_invalid_plan_tier(self):
        from app.schemas.organization import OrganizationCreate
        with pytest.raises(ValidationError):
            OrganizationCreate(name="Bad", plan_tier="gold")

    def test_organization_create_missing_name_raises(self):
        from app.schemas.organization import OrganizationCreate
        with pytest.raises(ValidationError):
            OrganizationCreate()

    def test_organization_create_empty_name_raises(self):
        from app.schemas.organization import OrganizationCreate
        with pytest.raises(ValidationError):
            OrganizationCreate(name="")

    def test_organization_create_seats_min_one(self):
        from app.schemas.organization import OrganizationCreate
        with pytest.raises(ValidationError):
            OrganizationCreate(name="Bad", seats=0)

    def test_organization_read_valid(self):
        from app.schemas.organization import OrganizationRead
        uid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        org = OrganizationRead(
            id=uid, name="Acme", plan_tier="free", seats=5, created_at=now
        )
        assert org.id == uid
        assert org.name == "Acme"

    def test_organization_update_all_optional(self):
        from app.schemas.organization import OrganizationUpdate
        upd = OrganizationUpdate()
        assert upd.name is None
        assert upd.plan_tier is None
        assert upd.seats is None

    def test_organization_update_partial(self):
        from app.schemas.organization import OrganizationUpdate
        upd = OrganizationUpdate(name="New Name")
        assert upd.name == "New Name"

    def test_organization_update_seats_must_be_positive(self):
        from app.schemas.organization import OrganizationUpdate
        with pytest.raises(ValidationError):
            OrganizationUpdate(seats=0)


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------
class TestUserSchemas:
    def test_user_create_valid(self):
        from app.schemas.user import UserCreate
        uid = uuid.uuid4()
        user = UserCreate(name="Alice", email="alice@example.com", org_id=uid)
        assert user.name == "Alice"
        assert user.email == "alice@example.com"
        assert user.role == "recruiter"

    def test_user_create_missing_name_raises(self):
        from app.schemas.user import UserCreate
        uid = uuid.uuid4()
        with pytest.raises(ValidationError):
            UserCreate(email="alice@example.com", org_id=uid)

    def test_user_create_missing_email_raises(self):
        from app.schemas.user import UserCreate
        uid = uuid.uuid4()
        with pytest.raises(ValidationError):
            UserCreate(name="Alice", org_id=uid)

    def test_user_create_invalid_email_raises(self):
        from app.schemas.user import UserCreate
        uid = uuid.uuid4()
        with pytest.raises(ValidationError):
            UserCreate(name="Alice", email="not-an-email", org_id=uid)

    def test_user_create_missing_org_id_raises(self):
        from app.schemas.user import UserCreate
        with pytest.raises(ValidationError):
            UserCreate(name="Alice", email="alice@example.com")

    def test_user_create_invalid_role_raises(self):
        from app.schemas.user import UserCreate
        uid = uuid.uuid4()
        with pytest.raises(ValidationError):
            UserCreate(name="Alice", email="alice@example.com", org_id=uid, role="superuser")

    def test_user_create_valid_roles(self):
        from app.schemas.user import UserCreate
        uid = uuid.uuid4()
        for role in ["admin", "recruiter", "viewer"]:
            user = UserCreate(name="Alice", email="alice@example.com", org_id=uid, role=role)
            assert user.role == role

    def test_user_read_valid(self):
        from app.schemas.user import UserRead
        uid = uuid.uuid4()
        org_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        user = UserRead(
            id=uid, name="Alice", email="alice@example.com",
            role="recruiter", org_id=org_id, created_at=now
        )
        assert user.id == uid

    def test_user_update_all_optional(self):
        from app.schemas.user import UserUpdate
        upd = UserUpdate()
        assert upd.name is None
        assert upd.role is None

    def test_user_update_partial(self):
        from app.schemas.user import UserUpdate
        upd = UserUpdate(name="Bob")
        assert upd.name == "Bob"

    def test_token_response_valid(self):
        from app.schemas.user import TokenResponse
        token = TokenResponse(access_token="my-token")
        assert token.access_token == "my-token"
        assert token.token_type == "bearer"

    def test_token_response_custom_type(self):
        from app.schemas.user import TokenResponse
        token = TokenResponse(access_token="tok", token_type="JWT")
        assert token.token_type == "JWT"

    def test_token_response_missing_access_token_raises(self):
        from app.schemas.user import TokenResponse
        with pytest.raises(ValidationError):
            TokenResponse()


# ---------------------------------------------------------------------------
# Candidate schemas
# ---------------------------------------------------------------------------
class TestCandidateSchemas:
    def test_candidate_create_valid(self):
        from app.schemas.candidate import CandidateCreate
        uid = uuid.uuid4()
        c = CandidateCreate(name="John Doe", org_id=uid)
        assert c.name == "John Doe"
        assert c.org_id == uid
        assert c.email is None
        assert c.phone is None
        assert c.location is None

    def test_candidate_create_missing_name_raises(self):
        from app.schemas.candidate import CandidateCreate
        uid = uuid.uuid4()
        with pytest.raises(ValidationError):
            CandidateCreate(org_id=uid)

    def test_candidate_create_empty_name_raises(self):
        from app.schemas.candidate import CandidateCreate
        uid = uuid.uuid4()
        with pytest.raises(ValidationError):
            CandidateCreate(name="", org_id=uid)

    def test_candidate_create_missing_org_id_raises(self):
        from app.schemas.candidate import CandidateCreate
        with pytest.raises(ValidationError):
            CandidateCreate(name="John")

    def test_candidate_create_with_email(self):
        from app.schemas.candidate import CandidateCreate
        uid = uuid.uuid4()
        c = CandidateCreate(name="John", email="john@example.com", org_id=uid)
        assert c.email == "john@example.com"

    def test_candidate_create_invalid_email_raises(self):
        from app.schemas.candidate import CandidateCreate
        uid = uuid.uuid4()
        with pytest.raises(ValidationError):
            CandidateCreate(name="John", email="bad-email", org_id=uid)

    def test_candidate_read_valid(self):
        from app.schemas.candidate import CandidateRead
        uid = uuid.uuid4()
        org_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        c = CandidateRead(
            id=uid, name="John", email=None, phone=None,
            location=None, org_id=org_id, created_at=now
        )
        assert c.id == uid

    def test_candidate_update_all_optional(self):
        from app.schemas.candidate import CandidateUpdate
        upd = CandidateUpdate()
        assert upd.name is None
        assert upd.email is None
        assert upd.phone is None
        assert upd.location is None

    def test_candidate_profile_read_valid(self):
        from app.schemas.candidate import CandidateProfileRead
        uid = uuid.uuid4()
        cand_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        prof = CandidateProfileRead(
            id=uid, candidate_id=cand_id, skills=["Python"],
            work_experience=None, education=None,
            languages=None, certifications=None,
            parse_status="done", parsed_at=now
        )
        assert prof.skills == ["Python"]

    def test_candidate_profile_update_all_optional(self):
        from app.schemas.candidate import CandidateProfileUpdate
        upd = CandidateProfileUpdate()
        assert upd.skills is None
        assert upd.work_experience is None
        assert upd.education is None


# ---------------------------------------------------------------------------
# Job schemas
# ---------------------------------------------------------------------------
class TestJobSchemas:
    def test_job_create_valid(self):
        from app.schemas.job import JobCreate
        uid = uuid.uuid4()
        job = JobCreate(title="Software Engineer", org_id=uid)
        assert job.title == "Software Engineer"
        assert job.status == "draft"
        assert job.jd_text is None

    def test_job_create_missing_title_raises(self):
        from app.schemas.job import JobCreate
        uid = uuid.uuid4()
        with pytest.raises(ValidationError):
            JobCreate(org_id=uid)

    def test_job_create_empty_title_raises(self):
        from app.schemas.job import JobCreate
        uid = uuid.uuid4()
        with pytest.raises(ValidationError):
            JobCreate(title="", org_id=uid)

    def test_job_create_missing_org_id_raises(self):
        from app.schemas.job import JobCreate
        with pytest.raises(ValidationError):
            JobCreate(title="Engineer")

    def test_job_create_valid_statuses(self):
        from app.schemas.job import JobCreate
        uid = uuid.uuid4()
        for status in ["draft", "active", "closed", "archived"]:
            job = JobCreate(title="Eng", org_id=uid, status=status)
            assert job.status == status

    def test_job_create_invalid_status_raises(self):
        from app.schemas.job import JobCreate
        uid = uuid.uuid4()
        with pytest.raises(ValidationError):
            JobCreate(title="Eng", org_id=uid, status="pending")

    def test_job_read_valid(self):
        from app.schemas.job import JobRead
        uid = uuid.uuid4()
        org_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        job = JobRead(
            id=uid, title="Engineer", org_id=org_id,
            jd_text=None, status="active", created_at=now
        )
        assert job.status == "active"

    def test_job_update_all_optional(self):
        from app.schemas.job import JobUpdate
        upd = JobUpdate()
        assert upd.title is None
        assert upd.jd_text is None
        assert upd.status is None

    def test_jd_profile_read_valid(self):
        from app.schemas.job import JDProfileRead
        uid = uuid.uuid4()
        job_id = uuid.uuid4()
        prof = JDProfileRead(
            id=uid, job_id=job_id,
            required_skills=["Python", "SQL"],
            nice_to_have_skills=["Kafka"],
            seniority="senior",
            experience_years_min=3,
            experience_years_max=7,
            responsibilities=None
        )
        assert prof.required_skills == ["Python", "SQL"]
        assert prof.experience_years_min == 3


# ---------------------------------------------------------------------------
# Match schemas
# ---------------------------------------------------------------------------
class TestMatchSchemas:
    def test_match_read_valid(self):
        from app.schemas.match import MatchRead
        uid = uuid.uuid4()
        cand_id = uuid.uuid4()
        job_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        m = MatchRead(
            id=uid, candidate_id=cand_id, job_id=job_id,
            overall_score=85, skill_score=90, experience_score=80,
            education_score=75, rationale="Good match", created_at=now
        )
        assert m.overall_score == 85
        assert m.rationale == "Good match"

    def test_match_read_null_scores(self):
        from app.schemas.match import MatchRead
        uid = uuid.uuid4()
        cand_id = uuid.uuid4()
        job_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        m = MatchRead(
            id=uid, candidate_id=cand_id, job_id=job_id,
            overall_score=None, skill_score=None,
            experience_score=None, education_score=None,
            rationale=None, created_at=now
        )
        assert m.overall_score is None

    def test_pipeline_read_valid(self):
        from app.schemas.match import PipelineRead
        uid = uuid.uuid4()
        job_id = uuid.uuid4()
        cand_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        p = PipelineRead(
            id=uid, job_id=job_id, candidate_id=cand_id,
            stage="screened", updated_at=now
        )
        assert p.stage == "screened"

    def test_pipeline_update_valid_stages(self):
        from app.schemas.match import PipelineUpdate
        for stage in ["sourced", "screened", "shortlisted", "interviewed", "offered", "hired", "rejected"]:
            upd = PipelineUpdate(stage=stage)
            assert upd.stage == stage

    def test_pipeline_update_invalid_stage_raises(self):
        from app.schemas.match import PipelineUpdate
        with pytest.raises(ValidationError):
            PipelineUpdate(stage="pending")

    def test_pipeline_update_missing_stage_raises(self):
        from app.schemas.match import PipelineUpdate
        with pytest.raises(ValidationError):
            PipelineUpdate()


# ---------------------------------------------------------------------------
# TalentPool schemas
# ---------------------------------------------------------------------------
class TestTalentPoolSchemas:
    def test_talent_pool_create_valid(self):
        from app.schemas.talent_pool import TalentPoolCreate
        uid = uuid.uuid4()
        tp = TalentPoolCreate(name="Senior Devs", org_id=uid)
        assert tp.name == "Senior Devs"
        assert tp.org_id == uid

    def test_talent_pool_create_missing_name_raises(self):
        from app.schemas.talent_pool import TalentPoolCreate
        uid = uuid.uuid4()
        with pytest.raises(ValidationError):
            TalentPoolCreate(org_id=uid)

    def test_talent_pool_create_empty_name_raises(self):
        from app.schemas.talent_pool import TalentPoolCreate
        uid = uuid.uuid4()
        with pytest.raises(ValidationError):
            TalentPoolCreate(name="", org_id=uid)

    def test_talent_pool_create_missing_org_id_raises(self):
        from app.schemas.talent_pool import TalentPoolCreate
        with pytest.raises(ValidationError):
            TalentPoolCreate(name="Pool A")

    def test_talent_pool_read_valid(self):
        from app.schemas.talent_pool import TalentPoolRead
        uid = uuid.uuid4()
        org_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        tp = TalentPoolRead(id=uid, name="Pool A", org_id=org_id, created_at=now)
        assert tp.name == "Pool A"

    def test_talent_pool_update_optional(self):
        from app.schemas.talent_pool import TalentPoolUpdate
        upd = TalentPoolUpdate()
        assert upd.name is None

    def test_talent_pool_update_with_name(self):
        from app.schemas.talent_pool import TalentPoolUpdate
        upd = TalentPoolUpdate(name="New Pool")
        assert upd.name == "New Pool"

    def test_talent_pool_member_add_valid(self):
        from app.schemas.talent_pool import TalentPoolMemberAdd
        uid = uuid.uuid4()
        m = TalentPoolMemberAdd(candidate_id=uid)
        assert m.candidate_id == uid

    def test_talent_pool_member_add_missing_raises(self):
        from app.schemas.talent_pool import TalentPoolMemberAdd
        with pytest.raises(ValidationError):
            TalentPoolMemberAdd()
