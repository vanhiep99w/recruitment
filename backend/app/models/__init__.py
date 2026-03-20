"""
SQLAlchemy models package.
Import all models here so that Alembic autogenerate detects them.
"""
from app.models.organization import Organization
from app.models.user import User
from app.models.candidate import Candidate
from app.models.candidate_profile import CandidateProfile
from app.models.cv import CV
from app.models.job import Job
from app.models.jd_profile import JDProfile
from app.models.match import Match
from app.models.pipeline import Pipeline
from app.models.talent_pool import TalentPool
from app.models.talent_pool_member import TalentPoolMember

__all__ = [
    "Organization",
    "User",
    "Candidate",
    "CandidateProfile",
    "CV",
    "Job",
    "JDProfile",
    "Match",
    "Pipeline",
    "TalentPool",
    "TalentPoolMember",
]
