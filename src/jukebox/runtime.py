"""Runtime assembly and startup probes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from .adapters.input import ReadableInput
from .adapters.input_evdev import EvdevScannerInput
from .adapters.playback_spotify import SpotifyPlaybackBackend
from .adapters.playback_stub import StubPlaybackBackend
from .config import Settings
from .core.models import PlaybackBackend
from .runtime_health import DependencyStatus, HealthMonitor, RuntimeHealthMonitor


@dataclass(frozen=True)
class RuntimeDependencies:
    """Assembled runtime dependencies for the controller loop."""

    input_stream: ReadableInput
    playback_backend: PlaybackBackend
    health_monitor: HealthMonitor
    source: str


@dataclass(frozen=True)
class StartupError(RuntimeError):
    """A startup failure that should be surfaced as an observable event."""

    code: str
    message: str
    reason_code: str | None = None
    backend: str | None = None
    device_name: str | None = None
    source: str | None = None

    def __str__(self) -> str:
        return self.message


def build_runtime(settings: Settings, default_stdin: ReadableInput) -> RuntimeDependencies:
    """Build runtime adapters and perform startup probes."""

    input_stream = _build_input_backend(settings, default_stdin)
    playback_backend = _build_playback_backend(settings)
    health_monitor = RuntimeHealthMonitor(
        scanner_status=_build_input_status_source(settings, input_stream).status,
        playback_status=cast(_StatusSource, playback_backend).status,
        poll_interval_seconds=settings.health_poll_interval_seconds,
        source=settings.input_backend,
    )

    return RuntimeDependencies(
        input_stream=input_stream,
        playback_backend=playback_backend,
        health_monitor=health_monitor,
        source=settings.input_backend,
    )


def _build_input_backend(settings: Settings, default_stdin: ReadableInput) -> ReadableInput:
    if settings.input_backend == "stdin":
        return default_stdin

    assert settings.scanner_device is not None
    return EvdevScannerInput(settings.scanner_device)


def _build_playback_backend(settings: Settings) -> PlaybackBackend:
    if settings.playback_backend == "spotify":
        assert settings.spotify_client_id is not None
        assert settings.spotify_client_secret is not None
        assert settings.spotify_refresh_token is not None
        return SpotifyPlaybackBackend(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            refresh_token=settings.spotify_refresh_token,
            device_id=settings.spotify_device_id,
            target_device_name=settings.spotify_target_device_name,
            confirmation_timeout_seconds=settings.spotify_confirm_timeout_seconds,
            confirmation_poll_interval_seconds=settings.spotify_confirm_poll_interval_seconds,
        )
    return StubPlaybackBackend()


class _StatusSource:
    def status(self) -> DependencyStatus:
        raise NotImplementedError


@dataclass(frozen=True)
class _StaticReadyStatusSource(_StatusSource):
    source: str | None = None
    backend: str | None = None

    def status(self) -> DependencyStatus:
        return DependencyStatus(
            code="ready",
            ready=True,
            message="waiting for scan input",
            source=self.source,
            backend=self.backend,
        )


def _build_input_status_source(settings: Settings, input_stream: ReadableInput) -> _StatusSource:
    if settings.input_backend == "stdin":
        return _StaticReadyStatusSource(source=settings.input_backend)
    return cast(_StatusSource, input_stream)
