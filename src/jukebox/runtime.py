"""Runtime assembly and startup probes."""

from __future__ import annotations

from dataclasses import dataclass

from .adapters.input import ReadableInput
from .adapters.input_evdev import EvdevScannerInput
from .adapters.playback_spotify import SpotifyPlaybackBackend
from .adapters.playback_stub import StubPlaybackBackend
from .config import Settings
from .core.models import PlaybackBackend


@dataclass(frozen=True)
class RuntimeDependencies:
    """Assembled runtime dependencies for the controller loop."""

    input_stream: ReadableInput
    playback_backend: PlaybackBackend
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
    probe_result = playback_backend.probe()
    if not probe_result.ok:
        raise StartupError(
            code="receiver_unavailable",
            message=probe_result.message or "Playback backend startup probe failed.",
            reason_code=probe_result.reason_code,
            backend=probe_result.backend,
            device_name=probe_result.device_name,
            source=settings.input_backend,
        )

    return RuntimeDependencies(
        input_stream=input_stream,
        playback_backend=playback_backend,
        source=settings.input_backend,
    )


def _build_input_backend(settings: Settings, default_stdin: ReadableInput) -> ReadableInput:
    if settings.input_backend == "stdin":
        return default_stdin

    assert settings.scanner_device is not None
    try:
        return EvdevScannerInput(settings.scanner_device)
    except OSError as exc:
        raise StartupError(
            code="scanner_unavailable",
            message=f"Scanner device unavailable: {exc}",
            reason_code="scanner_unavailable",
            source=settings.input_backend,
        ) from exc


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
