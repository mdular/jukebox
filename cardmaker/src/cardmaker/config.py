"""Immutable environment configuration for the Card Maker process."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final

_MARKET_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z]{2}$")
_LOG_LEVELS: Final[frozenset[str]] = frozenset(
    {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
)


class ConfigurationError(ValueError):
    """Raised when required process configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated Card Maker process settings."""

    spotify_client_id: str = field(repr=False)
    spotify_client_secret: str = field(repr=False)
    spotify_market: str
    http_bind: str = "127.0.0.1"
    http_port: int = 8081
    log_level: str = "INFO"

    @classmethod
    def from_environ(cls, environ: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if environ is None else environ
        client_id = _required(values, "CARDMAKER_SPOTIFY_CLIENT_ID")
        client_secret = _required(values, "CARDMAKER_SPOTIFY_CLIENT_SECRET")
        market = _required(values, "CARDMAKER_SPOTIFY_MARKET")
        if not _MARKET_PATTERN.fullmatch(market):
            raise ConfigurationError(
                "CARDMAKER_SPOTIFY_MARKET must be an explicit two-letter country code."
            )

        bind = values.get("CARDMAKER_HTTP_BIND", "127.0.0.1").strip()
        if not bind:
            raise ConfigurationError("CARDMAKER_HTTP_BIND must not be empty.")

        raw_port = values.get("CARDMAKER_HTTP_PORT", "8081").strip()
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ConfigurationError("CARDMAKER_HTTP_PORT must be an integer.") from exc
        if not 1 <= port <= 65535:
            raise ConfigurationError("CARDMAKER_HTTP_PORT must be between 1 and 65535.")

        log_level = values.get("CARDMAKER_LOG_LEVEL", "INFO").strip().upper()
        if log_level not in _LOG_LEVELS:
            raise ConfigurationError(
                "CARDMAKER_LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL."
            )

        return cls(
            spotify_client_id=client_id,
            spotify_client_secret=client_secret,
            spotify_market=market.upper(),
            http_bind=bind,
            http_port=port,
            log_level=log_level,
        )


def _required(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"Missing required environment variable: {name}")
    return value
