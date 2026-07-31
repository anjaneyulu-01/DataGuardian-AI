"""Response models shared across routers."""

from typing import Literal

from pydantic import BaseModel, Field


class ServiceInfo(BaseModel):
    """Payload of the service root endpoint."""

    project: str = Field(examples=["DataGuardian AI"])
    status: str = Field(examples=["running"])


class HealthStatus(BaseModel):
    """Liveness payload used by humans, Docker health checks, and CI."""

    status: Literal["ok", "degraded", "down"] = "ok"
    version: str
    environment: str


class ErrorResponse(BaseModel):
    """Shape returned by every handled error."""

    detail: str
