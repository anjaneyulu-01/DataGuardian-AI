"""LLM-layer error types.

Same philosophy as the DataHub integration: every failure is typed, derives
from ``DataGuardianError`` so the handlers in ``app.main`` render it as a
consistent envelope, and the type tells callers whether a retry could help.

Tomorrow's agent depends on that distinction: a rate limit means back off and
continue the run; a configuration error means the whole run is doomed and
should stop immediately.
"""

from fastapi import status

from app.core.exceptions import DataGuardianError


class LLMError(DataGuardianError):
    """Base class for every LLM-layer failure."""

    status_code = status.HTTP_502_BAD_GATEWAY


class LLMConfigurationError(LLMError):
    """The provider cannot run at all: missing API key, unknown model.

    Deterministic — retrying cannot help, and callers should fail fast with
    the actionable message rather than degrade quietly.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class LLMProviderNotSupportedError(LLMConfigurationError):
    """`LLM_PROVIDER` names a provider that is registered but not implemented."""


class LLMConnectionError(LLMError):
    """The provider API could not be reached. Transient — retryable."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class LLMTimeoutError(LLMError):
    """The provider accepted the request but did not answer in time.

    Retryable, but with care: reasoning models legitimately take long, so the
    timeout is generous (`LLM_TIMEOUT`) before this is raised at all.
    """

    status_code = status.HTTP_504_GATEWAY_TIMEOUT


class LLMRateLimitError(LLMError):
    """HTTP 429 from the provider. Transient — retryable with backoff."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class LLMAuthenticationError(LLMError):
    """The provider rejected our credentials (401/403).

    Mapped to 502, not 401: the caller of *our* API is not the party whose
    key is invalid.
    """


class LLMResponseError(LLMError):
    """The provider answered, but not usably.

    Covers malformed JSON where structured output was requested, empty
    completions, and schema-validation failures. Not retried by the transport
    layer — but ``structured_output`` makes one deliberate repair attempt,
    because 'almost-JSON' is the most common LLM failure mode and one nudge
    usually fixes it.
    """
