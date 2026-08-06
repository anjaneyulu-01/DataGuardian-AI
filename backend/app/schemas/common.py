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
    # Whether background scanning is running. Reported here rather than on a
    # new endpoint: it is process state this liveness payload already
    # describes, and the UI needs it for the scheduler status indicator.
    # Additive and optional, so existing consumers are unaffected.
    scheduler_enabled: bool = False


class ErrorResponse(BaseModel):
    """Shape returned by every handled error."""

    detail: str
