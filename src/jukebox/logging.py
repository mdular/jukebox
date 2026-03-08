"""Logging setup for the Jukebox scaffold."""

from __future__ import annotations

import json
import logging
from typing import Optional, TextIO

from .config import LogFormat


class JsonFormatter(logging.Formatter):
    """Serialize log records as compact JSON."""

    def __init__(self, *, environment: str) -> None:
        super().__init__()
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": self._environment,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def configure_logging(
    *, level: str, log_format: LogFormat, environment: str, stream: Optional[TextIO] = None
) -> None:
    """Configure the root logger for console or JSON output."""

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(stream)
    if log_format == "json":
        formatter: logging.Formatter = JsonFormatter(environment=environment)
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
