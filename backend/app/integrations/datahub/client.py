"""Transport layer for DataHub.

Owns exactly one concern: getting an HTTP request to DataHub and a response
back, with connection pooling, authentication, timeouts, and retries applied
consistently. It knows nothing about GraphQL or about governance.

Lifecycle: one client per process, created in the application lifespan and
closed on shutdown (see ``app.main``). Creating an ``AsyncClient`` per request
would discard the connection pool and re-run the TLS handshake every time.
"""

import logging
from types import TracebackType
from typing import Any, Self

import httpx

from app.config import Settings
from app.config import settings as default_settings
from app.integrations.datahub.exceptions import (
    DataHubAuthenticationError,
    DataHubConnectionError,
    DataHubTimeoutError,
)
from app.integrations.datahub.retry import RETRYABLE_STATUS_CODES, with_retry

logger = logging.getLogger(__name__)

# Sent on every request so DataHub's access logs identify the caller.
_USER_AGENT = "DataGuardian-AI/1.0 (+https://github.com/dataguardian-ai)"


class DataHubClient:
    """Thin async HTTP client bound to a single DataHub instance."""

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Build the client.

        Args:
            settings: Configuration source. Defaults to the app-wide singleton.
            transport: Overrides the HTTP transport. Tests inject
                ``httpx.MockTransport`` here; production leaves it ``None``.
        """
        self._settings = settings or default_settings
        self._base_url = self._settings.datahub_gms_url.rstrip("/")
        self._graphql_path = self._settings.datahub_graphql_path

        # Transport-level retries are off: retrying happens one layer up in
        # `retry.py`, where it can apply jittered backoff, log each attempt,
        # and cover read timeouts and 5xx as well as connect failures. Leaving
        # both enabled would multiply the attempt count.
        self._transport = transport or httpx.AsyncHTTPTransport(
            retries=0,
            verify=self._settings.datahub_verify_ssl,
        )

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._settings.datahub_timeout_seconds),
            transport=self._transport,
            headers=self._build_headers(),
            follow_redirects=True,
        )

    # -- Configuration --------------------------------------------------------

    def _build_headers(self) -> dict[str, str]:
        """Static headers for every request, including auth when configured."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        }
        if self._settings.datahub_token:
            headers["Authorization"] = f"Bearer {self._settings.datahub_token}"
        return headers

    @property
    def is_authenticated(self) -> bool:
        """Whether a token is configured.

        A local quickstart with metadata-service auth disabled works without
        one; every real deployment requires it.
        """
        return bool(self._settings.datahub_token)

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def graphql_url(self) -> str:
        """Fully-qualified GraphQL endpoint, for logs and error messages.

        Delegates to the settings property so the URL is assembled in exactly
        one place.
        """
        return self._settings.datahub_graphql_url

    # -- Requests -------------------------------------------------------------

    async def post_graphql(self, payload: dict[str, Any]) -> httpx.Response:
        """POST a GraphQL document. Response parsing belongs to `graphql.py`."""
        operation = str(payload.get("operationName") or "graphql")
        return await self._request_with_retry(
            "POST", self._graphql_path, description=operation, json=payload
        )

    async def get(self, path: str, *, retry: bool = True) -> httpx.Response:
        """GET a plain REST path on GMS.

        `retry=False` is for the health probe: a monitoring endpoint must
        answer quickly with the truth, not spend seconds retrying — the
        retries exist for real work, not for the check that reports outages.
        """
        if not retry:
            return await self._request("GET", path)
        return await self._request_with_retry("GET", path, description=f"GET {path}")

    async def _request_with_retry(
        self, method: str, path: str, description: str, **kwargs: Any
    ) -> httpx.Response:
        """Issue a request, retrying transient failures with backoff."""
        return await with_retry(
            lambda: self._request(method, path, **kwargs),
            attempts=self._settings.datahub_max_retries + 1,
            base_delay=self._settings.datahub_retry_base_delay_seconds,
            max_delay=self._settings.datahub_retry_max_delay_seconds,
            description=f"DataHub {description}",
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Issue one request, translating transport failures into typed errors.

        Only transport-level problems are handled here. HTTP status codes are
        left to the caller, except 401/403 which always mean the same thing
        and are worth failing fast on with an actionable message, and the
        transient 5xx family which is surfaced as a retryable error.
        """
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise DataHubTimeoutError(
                f"DataHub did not respond within "
                f"{self._settings.datahub_timeout_seconds}s ({method} {path})"
            ) from exc
        except httpx.TransportError as exc:
            # Covers ConnectError, ReadError, remote protocol errors, and
            # anything else where we never received a usable response.
            raise DataHubConnectionError(
                f"Could not reach DataHub at {self._base_url}: {exc}"
            ) from exc

        if response.status_code in (401, 403):
            hint = (
                "DATAHUB_TOKEN is not set"
                if not self.is_authenticated
                else "DATAHUB_TOKEN is invalid, expired, or lacks the "
                "required privilege"
            )
            raise DataHubAuthenticationError(
                f"DataHub rejected the request with HTTP {response.status_code}: {hint}"
            )

        if response.status_code in RETRYABLE_STATUS_CODES:
            # Raised as a connection error so the retry policy picks it up.
            # GMS answers 502/503 while it is still booting, which is exactly
            # when another attempt is worth making.
            raise DataHubConnectionError(
                f"DataHub returned a transient HTTP {response.status_code} "
                f"for {method} {path}"
            )

        return response

    # -- Lifecycle ------------------------------------------------------------

    async def aclose(self) -> None:
        """Release the connection pool. Called from the application lifespan."""
        await self._client.aclose()
        logger.debug("DataHub client closed")

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()
