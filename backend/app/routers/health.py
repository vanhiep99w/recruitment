"""Health check router."""
from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter
from pydantic import BaseModel

try:
    __version__ = version("recruitment-backend")
except PackageNotFoundError:
    __version__ = "0.1.0"

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str = __version__


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    """Returns service health status. Used by load balancers and uptime monitors."""
    return HealthResponse(status="ok")
