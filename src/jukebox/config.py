"""Configuration loading for the Jukebox scaffold."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final, Literal, Mapping, Optional

from .core.cards import PlaybackMode

LogFormat = Literal["console", "json"]
PlaybackBackendName = Literal["stub", "spotify"]
InputBackendName = Literal["stdin", "evdev"]

JUKEBOX_ENV: Final[str] = "JUKEBOX_ENV"
JUKEBOX_LOG_LEVEL: Final[str] = "JUKEBOX_LOG_LEVEL"
JUKEBOX_LOG_FORMAT: Final[str] = "JUKEBOX_LOG_FORMAT"
JUKEBOX_PLAYBACK_BACKEND: Final[str] = "JUKEBOX_PLAYBACK_BACKEND"
JUKEBOX_DUPLICATE_WINDOW_SECONDS: Final[str] = "JUKEBOX_DUPLICATE_WINDOW_SECONDS"
JUKEBOX_INPUT_BACKEND: Final[str] = "JUKEBOX_INPUT_BACKEND"
JUKEBOX_SCANNER_DEVICE: Final[str] = "JUKEBOX_SCANNER_DEVICE"
JUKEBOX_SPOTIFY_CLIENT_ID: Final[str] = "JUKEBOX_SPOTIFY_CLIENT_ID"
JUKEBOX_SPOTIFY_CLIENT_SECRET: Final[str] = "JUKEBOX_SPOTIFY_CLIENT_SECRET"
JUKEBOX_SPOTIFY_REFRESH_TOKEN: Final[str] = "JUKEBOX_SPOTIFY_REFRESH_TOKEN"
JUKEBOX_SPOTIFY_DEVICE_ID: Final[str] = "JUKEBOX_SPOTIFY_DEVICE_ID"
JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME: Final[str] = "JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME"
JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS: Final[str] = (
    "JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS"
)
JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS: Final[str] = (
    "JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS"
)
JUKEBOX_HEALTH_POLL_INTERVAL_SECONDS: Final[str] = "JUKEBOX_HEALTH_POLL_INTERVAL_SECONDS"
JUKEBOX_OPERATOR_HTTP_BIND: Final[str] = "JUKEBOX_OPERATOR_HTTP_BIND"
JUKEBOX_OPERATOR_HTTP_PORT: Final[str] = "JUKEBOX_OPERATOR_HTTP_PORT"
JUKEBOX_OPERATOR_STATE_PATH: Final[str] = "JUKEBOX_OPERATOR_STATE_PATH"
JUKEBOX_CONTROL_DEBOUNCE_SECONDS: Final[str] = "JUKEBOX_CONTROL_DEBOUNCE_SECONDS"
JUKEBOX_PLAYBACK_MODE_DEFAULT: Final[str] = "JUKEBOX_PLAYBACK_MODE_DEFAULT"
JUKEBOX_VOLUME_PRESET_LOW_PERCENT: Final[str] = "JUKEBOX_VOLUME_PRESET_LOW_PERCENT"
JUKEBOX_VOLUME_PRESET_MEDIUM_PERCENT: Final[str] = "JUKEBOX_VOLUME_PRESET_MEDIUM_PERCENT"
JUKEBOX_VOLUME_PRESET_HIGH_PERCENT: Final[str] = "JUKEBOX_VOLUME_PRESET_HIGH_PERCENT"
JUKEBOX_IDLE_SHUTDOWN_SECONDS: Final[str] = "JUKEBOX_IDLE_SHUTDOWN_SECONDS"
JUKEBOX_SETUP_AP_SSID: Final[str] = "JUKEBOX_SETUP_AP_SSID"
JUKEBOX_SETUP_AP_PASSPHRASE: Final[str] = "JUKEBOX_SETUP_AP_PASSPHRASE"
JUKEBOX_SETUP_FALLBACK_GRACE_SECONDS: Final[str] = "JUKEBOX_SETUP_FALLBACK_GRACE_SECONDS"
JUKEBOX_WIFI_HELPER_COMMAND: Final[str] = "JUKEBOX_WIFI_HELPER_COMMAND"
JUKEBOX_SPOTIFYD_AUTH_HELPER_COMMAND: Final[str] = "JUKEBOX_SPOTIFYD_AUTH_HELPER_COMMAND"
JUKEBOX_SHUTDOWN_HELPER_COMMAND: Final[str] = "JUKEBOX_SHUTDOWN_HELPER_COMMAND"

DEFAULT_ENV: Final[str] = "development"
DEFAULT_LOG_LEVEL: Final[str] = "INFO"
DEFAULT_LOG_FORMAT: Final[LogFormat] = "console"
DEFAULT_PLAYBACK_BACKEND: Final[PlaybackBackendName] = "stub"
DEFAULT_DUPLICATE_WINDOW_SECONDS: Final[float] = 2.0
DEFAULT_INPUT_BACKEND: Final[InputBackendName] = "stdin"
DEFAULT_SPOTIFY_CONFIRM_TIMEOUT_SECONDS: Final[float] = 5.0
DEFAULT_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS: Final[float] = 0.25
DEFAULT_HEALTH_POLL_INTERVAL_SECONDS: Final[float] = 5.0
DEFAULT_OPERATOR_HTTP_BIND: Final[str] = "127.0.0.1"
DEFAULT_OPERATOR_HTTP_PORT: Final[int] = 8080
DEFAULT_OPERATOR_STATE_PATH: Final[str] = "/var/lib/jukebox/state.json"
DEFAULT_CONTROL_DEBOUNCE_SECONDS: Final[float] = 1.0
DEFAULT_PLAYBACK_MODE: Final[PlaybackMode] = "replace"
DEFAULT_VOLUME_PRESET_LOW_PERCENT: Final[int] = 35
DEFAULT_VOLUME_PRESET_MEDIUM_PERCENT: Final[int] = 55
DEFAULT_VOLUME_PRESET_HIGH_PERCENT: Final[int] = 75
DEFAULT_SETUP_FALLBACK_GRACE_SECONDS: Final[float] = 120.0
DEFAULT_WIFI_HELPER_COMMAND: Final[str] = "/usr/local/libexec/jukebox-wifi-helper"
DEFAULT_SPOTIFYD_AUTH_HELPER_COMMAND: Final[str] = (
    "/usr/local/libexec/jukebox-spotifyd-auth-helper"
)
DEFAULT_SHUTDOWN_HELPER_COMMAND: Final[str] = "/usr/local/libexec/jukebox-shutdown-helper"

_ALLOWED_LOG_LEVELS: Final[frozenset[str]] = frozenset(
    {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
)
_ALLOWED_LOG_FORMATS: Final[frozenset[str]] = frozenset({"console", "json"})
_ALLOWED_PLAYBACK_BACKENDS: Final[frozenset[str]] = frozenset({"stub", "spotify"})
_ALLOWED_INPUT_BACKENDS: Final[frozenset[str]] = frozenset({"stdin", "evdev"})
_ALLOWED_PLAYBACK_MODES: Final[frozenset[str]] = frozenset({"replace", "queue_tracks"})


class ConfigError(ValueError):
    """Raised when the Jukebox environment configuration is invalid."""


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the application."""

    environment: str
    log_level: str
    log_format: LogFormat
    playback_backend: PlaybackBackendName
    duplicate_window_seconds: float
    input_backend: InputBackendName
    scanner_device: str | None
    spotify_client_id: str | None
    spotify_client_secret: str | None
    spotify_refresh_token: str | None
    spotify_device_id: str | None
    spotify_target_device_name: str | None
    spotify_confirm_timeout_seconds: float
    spotify_confirm_poll_interval_seconds: float
    health_poll_interval_seconds: float
    operator_http_bind: str
    operator_http_port: int
    operator_state_path: str
    control_debounce_seconds: float
    playback_mode_default: PlaybackMode
    volume_preset_low_percent: int
    volume_preset_medium_percent: int
    volume_preset_high_percent: int
    idle_shutdown_seconds: float | None
    setup_ap_ssid: str | None
    setup_ap_passphrase: str | None
    setup_fallback_grace_seconds: float
    wifi_helper_command: str
    spotifyd_auth_helper_command: str
    shutdown_helper_command: str


def from_env(env: Optional[Mapping[str, str]] = None) -> Settings:
    """Build settings from environment variables."""

    source = os.environ if env is None else env
    environment = _read_environment(source)
    log_level = _read_log_level(source)
    log_format = _read_log_format(source)
    playback_backend = _read_playback_backend(source)
    duplicate_window_seconds = _read_duplicate_window_seconds(source)
    input_backend = _read_input_backend(source)
    scanner_device = _read_optional_value(source, JUKEBOX_SCANNER_DEVICE)
    spotify_client_id = _read_optional_value(source, JUKEBOX_SPOTIFY_CLIENT_ID)
    spotify_client_secret = _read_optional_value(source, JUKEBOX_SPOTIFY_CLIENT_SECRET)
    spotify_refresh_token = _read_optional_value(source, JUKEBOX_SPOTIFY_REFRESH_TOKEN)
    spotify_device_id = _read_optional_value(source, JUKEBOX_SPOTIFY_DEVICE_ID)
    spotify_target_device_name = _read_optional_value(source, JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME)
    spotify_confirm_timeout_seconds = _read_positive_float(
        source,
        JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS,
        default=DEFAULT_SPOTIFY_CONFIRM_TIMEOUT_SECONDS,
    )
    spotify_confirm_poll_interval_seconds = _read_positive_float(
        source,
        JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS,
        default=DEFAULT_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS,
    )
    health_poll_interval_seconds = _read_positive_float(
        source,
        JUKEBOX_HEALTH_POLL_INTERVAL_SECONDS,
        default=DEFAULT_HEALTH_POLL_INTERVAL_SECONDS,
    )
    operator_http_bind = _read_non_empty_string(
        source, JUKEBOX_OPERATOR_HTTP_BIND, default=DEFAULT_OPERATOR_HTTP_BIND
    )
    operator_http_port = _read_port(source, JUKEBOX_OPERATOR_HTTP_PORT)
    operator_state_path = _read_non_empty_string(
        source, JUKEBOX_OPERATOR_STATE_PATH, default=DEFAULT_OPERATOR_STATE_PATH
    )
    control_debounce_seconds = _read_positive_float(
        source,
        JUKEBOX_CONTROL_DEBOUNCE_SECONDS,
        default=DEFAULT_CONTROL_DEBOUNCE_SECONDS,
    )
    playback_mode_default = _read_playback_mode_default(source)
    volume_preset_low_percent = _read_percentage(
        source,
        JUKEBOX_VOLUME_PRESET_LOW_PERCENT,
        default=DEFAULT_VOLUME_PRESET_LOW_PERCENT,
    )
    volume_preset_medium_percent = _read_percentage(
        source,
        JUKEBOX_VOLUME_PRESET_MEDIUM_PERCENT,
        default=DEFAULT_VOLUME_PRESET_MEDIUM_PERCENT,
    )
    volume_preset_high_percent = _read_percentage(
        source,
        JUKEBOX_VOLUME_PRESET_HIGH_PERCENT,
        default=DEFAULT_VOLUME_PRESET_HIGH_PERCENT,
    )
    idle_shutdown_seconds = _read_optional_positive_float(source, JUKEBOX_IDLE_SHUTDOWN_SECONDS)
    setup_ap_ssid = _read_optional_value(source, JUKEBOX_SETUP_AP_SSID)
    setup_ap_passphrase = _read_optional_value(source, JUKEBOX_SETUP_AP_PASSPHRASE)
    setup_fallback_grace_seconds = _read_positive_float(
        source,
        JUKEBOX_SETUP_FALLBACK_GRACE_SECONDS,
        default=DEFAULT_SETUP_FALLBACK_GRACE_SECONDS,
    )
    wifi_helper_command = _read_non_empty_string(
        source, JUKEBOX_WIFI_HELPER_COMMAND, default=DEFAULT_WIFI_HELPER_COMMAND
    )
    spotifyd_auth_helper_command = _read_non_empty_string(
        source,
        JUKEBOX_SPOTIFYD_AUTH_HELPER_COMMAND,
        default=DEFAULT_SPOTIFYD_AUTH_HELPER_COMMAND,
    )
    shutdown_helper_command = _read_non_empty_string(
        source, JUKEBOX_SHUTDOWN_HELPER_COMMAND, default=DEFAULT_SHUTDOWN_HELPER_COMMAND
    )
    settings = Settings(
        environment=environment,
        log_level=log_level,
        log_format=log_format,
        playback_backend=playback_backend,
        duplicate_window_seconds=duplicate_window_seconds,
        input_backend=input_backend,
        scanner_device=scanner_device,
        spotify_client_id=spotify_client_id,
        spotify_client_secret=spotify_client_secret,
        spotify_refresh_token=spotify_refresh_token,
        spotify_device_id=spotify_device_id,
        spotify_target_device_name=spotify_target_device_name,
        spotify_confirm_timeout_seconds=spotify_confirm_timeout_seconds,
        spotify_confirm_poll_interval_seconds=spotify_confirm_poll_interval_seconds,
        health_poll_interval_seconds=health_poll_interval_seconds,
        operator_http_bind=operator_http_bind,
        operator_http_port=operator_http_port,
        operator_state_path=operator_state_path,
        control_debounce_seconds=control_debounce_seconds,
        playback_mode_default=playback_mode_default,
        volume_preset_low_percent=volume_preset_low_percent,
        volume_preset_medium_percent=volume_preset_medium_percent,
        volume_preset_high_percent=volume_preset_high_percent,
        idle_shutdown_seconds=idle_shutdown_seconds,
        setup_ap_ssid=setup_ap_ssid,
        setup_ap_passphrase=setup_ap_passphrase,
        setup_fallback_grace_seconds=setup_fallback_grace_seconds,
        wifi_helper_command=wifi_helper_command,
        spotifyd_auth_helper_command=spotifyd_auth_helper_command,
        shutdown_helper_command=shutdown_helper_command,
    )
    _validate_backend_settings(settings)
    return settings


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


def _read_playback_backend(source: Mapping[str, str]) -> PlaybackBackendName:
    raw_value = source.get(JUKEBOX_PLAYBACK_BACKEND)
    if raw_value is None:
        return DEFAULT_PLAYBACK_BACKEND

    value = raw_value.strip().lower()
    if value not in _ALLOWED_PLAYBACK_BACKENDS:
        allowed = ", ".join(sorted(_ALLOWED_PLAYBACK_BACKENDS))
        raise ConfigError(f"{JUKEBOX_PLAYBACK_BACKEND} must be one of: {allowed}.")
    return value  # type: ignore[return-value]


def _read_duplicate_window_seconds(source: Mapping[str, str]) -> float:
    return _read_positive_float(
        source,
        JUKEBOX_DUPLICATE_WINDOW_SECONDS,
        default=DEFAULT_DUPLICATE_WINDOW_SECONDS,
    )


def _read_input_backend(source: Mapping[str, str]) -> InputBackendName:
    raw_value = source.get(JUKEBOX_INPUT_BACKEND)
    if raw_value is None:
        return DEFAULT_INPUT_BACKEND

    value = raw_value.strip().lower()
    if value not in _ALLOWED_INPUT_BACKENDS:
        allowed = ", ".join(sorted(_ALLOWED_INPUT_BACKENDS))
        raise ConfigError(f"{JUKEBOX_INPUT_BACKEND} must be one of: {allowed}.")
    return value  # type: ignore[return-value]


def _read_non_empty_string(source: Mapping[str, str], key: str, *, default: str) -> str:
    raw_value = source.get(key)
    if raw_value is None:
        return default

    value = raw_value.strip()
    if not value:
        raise ConfigError(f"{key} must not be empty.")
    return value


def _read_optional_positive_float(source: Mapping[str, str], key: str) -> float | None:
    raw_value = source.get(key)
    if raw_value is None:
        return None

    value = raw_value.strip()
    if value == "":
        return None

    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a positive float.") from exc

    if parsed <= 0:
        raise ConfigError(f"{key} must be a positive float.")
    return parsed


def _read_positive_float(source: Mapping[str, str], key: str, *, default: float) -> float:
    raw_value = source.get(key)
    if raw_value is None:
        return default

    value = raw_value.strip()
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a positive float.") from exc

    if parsed <= 0:
        raise ConfigError(f"{key} must be a positive float.")
    return parsed


def _read_optional_value(source: Mapping[str, str], key: str) -> str | None:
    raw_value = source.get(key)
    if raw_value is None:
        return None

    value = raw_value.strip()
    return value or None


def _read_playback_mode_default(source: Mapping[str, str]) -> PlaybackMode:
    raw_value = source.get(JUKEBOX_PLAYBACK_MODE_DEFAULT)
    if raw_value is None:
        return DEFAULT_PLAYBACK_MODE

    value = raw_value.strip().lower()
    if value not in _ALLOWED_PLAYBACK_MODES:
        allowed = ", ".join(sorted(_ALLOWED_PLAYBACK_MODES))
        raise ConfigError(f"{JUKEBOX_PLAYBACK_MODE_DEFAULT} must be one of: {allowed}.")
    return value  # type: ignore[return-value]


def _read_port(source: Mapping[str, str], key: str) -> int:
    raw_value = source.get(key)
    if raw_value is None:
        return DEFAULT_OPERATOR_HTTP_PORT

    value = raw_value.strip()
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer port between 1 and 65535.") from exc
    if parsed < 1 or parsed > 65535:
        raise ConfigError(f"{key} must be an integer port between 1 and 65535.")
    return parsed


def _read_percentage(source: Mapping[str, str], key: str, *, default: int) -> int:
    raw_value = source.get(key)
    if raw_value is None:
        return default

    value = raw_value.strip()
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer between 0 and 100.") from exc
    if parsed < 0 or parsed > 100:
        raise ConfigError(f"{key} must be an integer between 0 and 100.")
    return parsed


def _validate_backend_settings(settings: Settings) -> None:
    if settings.spotify_confirm_poll_interval_seconds > settings.spotify_confirm_timeout_seconds:
        raise ConfigError(
            f"{JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS} must not exceed "
            f"{JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS}."
        )

    if settings.input_backend == "evdev" and settings.scanner_device is None:
        raise ConfigError(
            f"{JUKEBOX_INPUT_BACKEND}=evdev requires {JUKEBOX_SCANNER_DEVICE}."
        )

    if (
        settings.setup_ap_passphrase is not None
        and len(settings.setup_ap_passphrase) < 8
    ):
        raise ConfigError(
            f"{JUKEBOX_SETUP_AP_PASSPHRASE} must be at least 8 characters long."
        )

    if settings.playback_backend != "spotify":
        return

    missing = [
        key
        for key, value in (
            (JUKEBOX_SPOTIFY_CLIENT_ID, settings.spotify_client_id),
            (JUKEBOX_SPOTIFY_CLIENT_SECRET, settings.spotify_client_secret),
            (JUKEBOX_SPOTIFY_REFRESH_TOKEN, settings.spotify_refresh_token),
        )
        if value is None
    ]
    if missing:
        joined = ", ".join(missing)
        raise ConfigError(
            f"{JUKEBOX_PLAYBACK_BACKEND}=spotify requires these variables: {joined}."
        )

    if settings.spotify_device_id is None and settings.spotify_target_device_name is None:
        raise ConfigError(
            f"{JUKEBOX_PLAYBACK_BACKEND}=spotify requires either "
            f"{JUKEBOX_SPOTIFY_DEVICE_ID} or {JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME}."
        )

    if (
        settings.spotify_confirm_poll_interval_seconds
        > settings.spotify_confirm_timeout_seconds
    ):
        raise ConfigError(
            f"{JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS} must be less than or equal to "
            f"{JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS}."
        )
