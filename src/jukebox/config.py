"""Configuration loading for the Jukebox scaffold."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final, Literal, Mapping, Optional

LogFormat = Literal["console", "json"]

JUKEBOX_ENV: Final[str] = "JUKEBOX_ENV"
JUKEBOX_LOG_LEVEL: Final[str] = "JUKEBOX_LOG_LEVEL"
JUKEBOX_LOG_FORMAT: Final[str] = "JUKEBOX_LOG_FORMAT"

DEFAULT_ENV: Final[str] = "development"
DEFAULT_LOG_LEVEL: Final[str] = "INFO"
DEFAULT_LOG_FORMAT: Final[LogFormat] = "console"

_ALLOWED_LOG_LEVELS: Final[frozenset[str]] = frozenset(
    {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
)
_ALLOWED_LOG_FORMATS: Final[frozenset[str]] = frozenset({"console", "json"})


class ConfigError(ValueError):
    """Raised when the Jukebox environment configuration is invalid."""


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the scaffolded application."""

    environment: str
    log_level: str
    log_format: LogFormat


def from_env(env: Optional[Mapping[str, str]] = None) -> Settings:
    """Build settings from environment variables."""

    source = os.environ if env is None else env
    environment = _read_environment(source)
    log_level = _read_log_level(source)
    log_format = _read_log_format(source)
    return Settings(environment=environment, log_level=log_level, log_format=log_format)


def _read_environment(source: Mapping[str, str]) -> str:
    raw_value = source.get(JUKEBOX_ENV)
    if raw_value is None:
        return DEFAULT_ENV

    value = raw_value.strip()
    if not value:
        raise ConfigError(f"{JUKEBOX_ENV} must not be empty.")
    return value


def _read_log_level(source: Mapping[str, str]) -> str:
    raw_value = source.get(JUKEBOX_LOG_LEVEL)
    if raw_value is None:
        return DEFAULT_LOG_LEVEL

    value = raw_value.strip().upper()
    if value not in _ALLOWED_LOG_LEVELS:
        allowed = ", ".join(sorted(_ALLOWED_LOG_LEVELS))
        raise ConfigError(f"{JUKEBOX_LOG_LEVEL} must be one of: {allowed}.")
    return value


def _read_log_format(source: Mapping[str, str]) -> LogFormat:
    raw_value = source.get(JUKEBOX_LOG_FORMAT)
    if raw_value is None:
        return DEFAULT_LOG_FORMAT

    value = raw_value.strip().lower()
    if value not in _ALLOWED_LOG_FORMATS:
        allowed = ", ".join(sorted(_ALLOWED_LOG_FORMATS))
        raise ConfigError(f"{JUKEBOX_LOG_FORMAT} must be one of: {allowed}.")
    return value  # type: ignore[return-value]
