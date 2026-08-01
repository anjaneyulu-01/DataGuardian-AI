"""DataHub-specific error types.

Every exception here derives from ``DataGuardianError``, so the handlers
registered in ``app.main`` translate them into the standard
``{"detail": ...}`` envelope with the right HTTP status. Nothing in this
module imports FastAPI beyond the status constants.

The distinction between these types matters to callers: a timeout or a
connection failure is worth retrying, while an authentication or a query error
is not. Tomorrow's agent uses that difference to decide whether to back off or
to give up on a scan.
"""

from fastapi import status

from app.core.exceptions import DataGuardianError


class DataHubError(DataGuardianError):
    """Base class for every DataHub integration failure."""

    status_code = status.HTTP_502_BAD_GATEWAY


class DataHubConnectionError(DataHubError):
    """DataHub could not be reached at all (DNS, refused, reset).

    Surfaced as 503 rather than 502: the upstream did not answer, so the
    condition is transient and the caller may retry.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class DataHubTimeoutError(DataHubError):
    """DataHub accepted the connection but did not answer in time."""

    status_code = status.HTTP_504_GATEWAY_TIMEOUT


class DataHubAuthenticationError(DataHubError):
    """DataHub rejected our credentials (HTTP 401/403).

    Deliberately *not* mapped to 401, which would wrongly imply the caller of
    *our* API is unauthenticated. This is a server-side misconfiguration:
    `DATAHUB_TOKEN` is missing, expired, or lacks the required privilege.
    """

    status_code = status.HTTP_502_BAD_GATEWAY


class DataHubResponseError(DataHubError):
    """DataHub returned something that is not a valid GraphQL response."""


class DataHubQueryError(DataHubError):
    """DataHub executed the query and reported GraphQL errors.

    Usually a schema mismatch: the query asks for a field this DataHub version
    does not expose. ``errors`` holds the raw GraphQL error list for logging.
    """

    def __init__(self, detail: str, errors: list[dict[str, object]] | None = None):
        super().__init__(detail)
        self.errors = errors or []


class DataHubEntityNotFoundError(DataHubError):
    """A requested URN does not exist in DataHub.

    GraphQL reports this as a ``null`` entity with HTTP 200, so the service
    layer raises it explicitly rather than returning an empty model.
    """

    status_code = status.HTTP_404_NOT_FOUND
