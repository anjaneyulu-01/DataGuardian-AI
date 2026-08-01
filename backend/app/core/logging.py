"""Logging setup.

Called once from the application lifespan so that every module can simply do
``logging.getLogger(__name__)`` and get consistently formatted output.
"""

import logging
import sys

from app.config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# Libraries whose DEBUG output is per-socket noise. At DEBUG level httpcore
# logs every connection, header write, and chunk read, which buries our own
# records and costs real throughput under load. Their INFO and above still
# come through.
_NOISY_LIBRARIES = ("httpcore", "httpx", "hpack", "apscheduler.scheduler")


def configure_logging() -> None:
    """Attach a single stdout handler to the root logger."""
    level = logging.DEBUG if settings.debug else logging.INFO

    root = logging.getLogger()
    root.setLevel(level)

    # Avoid stacking duplicate handlers when uvicorn reloads the module.
    for existing in list(root.handlers):
        root.removeHandler(existing)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)

    # Uvicorn installs its own handlers; let records propagate to ours instead.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True

    # Keep third-party transport chatter out of the application log, even when
    # the app itself is running at DEBUG.
    for name in _NOISY_LIBRARIES:
        logging.getLogger(name).setLevel(max(level, logging.INFO))
