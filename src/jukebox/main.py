"""Top-level runtime entrypoint for the Jukebox scaffold."""

from __future__ import annotations

import logging
import sys

from .config import ConfigError, from_env
from .logging import configure_logging

LOGGER = logging.getLogger("jukebox.main")


def main() -> int:
    """Load configuration, initialize logging, and exit."""

    try:
        settings = from_env()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    configure_logging(
        level=settings.log_level,
        log_format=settings.log_format,
        environment=settings.environment,
    )
    LOGGER.info("jukebox scaffold initialized; controller loop is not implemented yet")
    return 0
