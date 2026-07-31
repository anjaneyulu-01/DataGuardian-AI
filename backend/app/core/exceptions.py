"""Application exception types and their HTTP translation.

Handlers are registered in ``app.main`` so that any layer can raise a domain
error without importing FastAPI.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class DataGuardianError(Exception):
    """Base class for all expected application errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(DataGuardianError):
    """A requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND


class ExternalServiceError(DataGuardianError):
    """An upstream dependency (DataHub, Gemini, MCP) failed."""

    status_code = status.HTTP_502_BAD_GATEWAY


def register_exception_handlers(app: FastAPI) -> None:
    """Map application errors onto a consistent ``{"detail": ...}`` envelope."""

    @app.exception_handler(DataGuardianError)
    async def handle_known_error(
        _request: Request, exc: DataGuardianError
    ) -> JSONResponse:
        logger.warning("%s: %s", type(exc).__name__, exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
