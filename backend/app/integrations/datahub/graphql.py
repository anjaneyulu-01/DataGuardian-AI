"""GraphQL execution against DataHub.

Sits between the transport (`client.py`) and the domain logic (`service.py`),
and is the single place that understands the GraphQL response envelope:

    {"data": {...}, "errors": [...]}

GraphQL answers with HTTP 200 even when the query failed, so a naive
``response.json()["data"]`` silently yields ``None`` and the failure surfaces
much later as a confusing mapping error. Every response passes through
``execute`` so that never happens.
"""

import logging
from typing import Any

from app.integrations.datahub.client import DataHubClient
from app.integrations.datahub.exceptions import (
    DataHubQueryError,
    DataHubResponseError,
)

logger = logging.getLogger(__name__)


class GraphQLClient:
    """Executes GraphQL documents and returns the validated ``data`` object."""

    def __init__(self, client: DataHubClient) -> None:
        self._client = client

    async def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
    ) -> dict[str, Any]:
        """Run a GraphQL document and return its ``data`` payload.

        Args:
            query: The GraphQL document (see `queries.py`).
            variables: Query variables. Always prefer these over string
                interpolation — DataHub URNs contain characters that would
                otherwise need escaping, and interpolation invites injection.
            operation_name: Named operation, when the document defines several.

        Returns:
            The ``data`` object. Never ``None``.

        Raises:
            DataHubResponseError: The body was not a valid GraphQL response.
            DataHubQueryError: DataHub reported GraphQL errors.
            DataHubConnectionError / DataHubTimeoutError /
            DataHubAuthenticationError: Propagated from the transport.
        """
        payload: dict[str, Any] = {"query": query, "variables": variables or {}}
        if operation_name:
            payload["operationName"] = operation_name

        logger.debug(
            "DataHub GraphQL request: operation=%s variables=%s",
            operation_name or "<anonymous>",
            variables,
        )

        response = await self._client.post_graphql(payload)

        # A non-2xx here is a genuine HTTP failure (5xx, bad gateway, an HTML
        # error page from a proxy). 401/403 were already handled downstream.
        if response.status_code >= 400:
            raise DataHubResponseError(
                f"DataHub returned HTTP {response.status_code} for operation "
                f"'{operation_name or 'unknown'}': {_preview(response.text)}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            # Almost always a proxy or login page returning HTML instead of
            # JSON — worth showing a snippet so the cause is obvious.
            raise DataHubResponseError(
                f"DataHub returned a non-JSON response for operation "
                f"'{operation_name or 'unknown'}': {_preview(response.text)}"
            ) from exc

        if not isinstance(body, dict):
            raise DataHubResponseError(
                f"Expected a JSON object from DataHub, got {type(body).__name__}"
            )

        if errors := body.get("errors"):
            self._raise_for_errors(errors, operation_name)

        data = body.get("data")
        if data is None:
            raise DataHubResponseError(
                f"DataHub returned no 'data' for operation "
                f"'{operation_name or 'unknown'}'"
            )
        if not isinstance(data, dict):
            raise DataHubResponseError(
                f"Expected 'data' to be an object, got {type(data).__name__}"
            )

        return data

    def _raise_for_errors(self, errors: Any, operation_name: str | None) -> None:
        """Turn a GraphQL ``errors`` array into a typed exception."""
        if not isinstance(errors, list):
            raise DataHubResponseError(
                f"Expected 'errors' to be a list, got {type(errors).__name__}"
            )

        normalised = [e for e in errors if isinstance(e, dict)]
        messages = [str(e.get("message", "unknown error")) for e in normalised] or [
            "unknown GraphQL error"
        ]

        logger.error(
            "DataHub GraphQL errors for operation '%s': %s",
            operation_name or "<anonymous>",
            messages,
        )
        raise DataHubQueryError(
            f"DataHub rejected operation '{operation_name or 'unknown'}': "
            f"{'; '.join(messages)}",
            errors=normalised,
        )


def _preview(text: str, limit: int = 200) -> str:
    """Trim an error body so logs stay readable."""
    collapsed = " ".join(text.split())
    return collapsed[:limit] + "…" if len(collapsed) > limit else collapsed
