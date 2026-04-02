"""Runtime assembly and startup probes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from .adapters.action_router import ActionRouter
from .adapters.input import ReadableInput
from .adapters.input_evdev import EvdevScannerInput
from .adapters.playback_spotify import SpotifyPlaybackBackend
from .adapters.playback_stub import StubPlaybackBackend
from .adapters.system_helpers import CommandSystemHelpers
from .config import Settings
from .core.models import EventSink, PlaybackBackend
from .feedback_state import FeedbackStateTracker
from .idle_monitor import IdleMonitor
from .operator_server import OperatorHttpServer
from .operator_state import OperatorStateStore
from .runtime_health import DependencyStatus, HealthMonitor, RuntimeHealthMonitor
from .setup_mode import SetupModeManager


@dataclass(frozen=True)
class RuntimeDependencies:
    """Assembled runtime dependencies for the controller loop."""

    input_stream: ReadableInput
    playback_backend: PlaybackBackend
    health_monitor: HealthMonitor
    source: str
    action_router: ActionRouter | None = None
    operator_state: OperatorStateStore | None = None
    event_sinks: tuple[EventSink, ...] = ()
    services: tuple["LifecycleService", ...] = ()


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


class LifecycleService(Protocol):
    """Lifecycle contract for runtime-owned background services."""

    def start(self) -> None:
        """Start the service."""

    def stop(self) -> None:
        """Stop the service."""


def build_runtime(settings: Settings, default_stdin: ReadableInput) -> RuntimeDependencies:
    """Build runtime adapters and perform startup probes."""

    input_stream = _build_input_backend(settings, default_stdin)
    input_status_source = _build_input_status_source(settings, input_stream)
    playback_backend = _build_playback_backend(settings)
    operator_state = OperatorStateStore(settings.operator_state_path)
    feedback_tracker = FeedbackStateTracker()
    system_helpers = CommandSystemHelpers(
        wifi_helper_command=settings.wifi_helper_command,
        spotifyd_auth_helper_command=settings.spotifyd_auth_helper_command,
        shutdown_helper_command=settings.shutdown_helper_command,
    )
    setup_mode = SetupModeManager(
        operator_state=operator_state,
        wifi_helper=system_helpers,
        fallback_grace_seconds=settings.setup_fallback_grace_seconds,
    )
    try:
        setup_mode.initialize()
    except RuntimeError:
        pass
    action_router = ActionRouter(
        playback_backend=playback_backend,
        operator_state=operator_state,
        system_helpers=system_helpers,
        volume_presets={
            "low": settings.volume_preset_low_percent,
            "medium": settings.volume_preset_medium_percent,
            "high": settings.volume_preset_high_percent,
        },
    )
    idle_monitor = IdleMonitor(
        idle_shutdown_seconds=settings.idle_shutdown_seconds,
        player_active=playback_backend.player_active,
        shutdown_callback=lambda reason: system_helpers.request_shutdown(reason=reason),
    )
    operator_server = OperatorHttpServer(
        bind=settings.operator_http_bind,
        port=settings.operator_http_port,
        feedback_snapshot=feedback_tracker.snapshot,
        runtime_status=lambda: _build_runtime_status(
            settings=settings,
            operator_state=operator_state,
            scanner_status=input_status_source.status(),
            playback_status=cast(_StatusSource, playback_backend).status(),
            setup_status=setup_mode.status(),
            idle_status=idle_monitor.status(),
        ),
        submit_wifi=system_helpers.apply_wifi,
        start_auth=system_helpers.start_auth,
    )
    health_monitor = RuntimeHealthMonitor(
        scanner_status=input_status_source.status,
        playback_status=cast(_StatusSource, playback_backend).status,
        setup_status=setup_mode.status,
        poll_interval_seconds=settings.health_poll_interval_seconds,
        source=settings.input_backend,
    )

    return RuntimeDependencies(
        input_stream=input_stream,
        playback_backend=playback_backend,
        health_monitor=health_monitor,
        source=settings.input_backend,
        action_router=action_router,
        operator_state=operator_state,
        event_sinks=(feedback_tracker, idle_monitor),
        services=(operator_server, idle_monitor),
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


def _build_runtime_status(
    *,
    settings: Settings,
    operator_state: OperatorStateStore,
    scanner_status: DependencyStatus,
    playback_status: DependencyStatus,
    setup_status: DependencyStatus,
    idle_status: dict[str, object],
) -> dict[str, object]:
    state = operator_state.load()
    return {
        "playback_mode": state.playback_mode,
        "setup_required": setup_status.code == "setup_required",
        "auth_required": setup_status.code == "auth_required",
        "enabled_actions": sorted(state.enabled_actions),
        "scanner": _dependency_status_payload(scanner_status),
        "playback": _dependency_status_payload(playback_status),
        "setup": _dependency_status_payload(setup_status),
        "config": {
            "operator_http_bind": settings.operator_http_bind,
            "operator_http_port": settings.operator_http_port,
            "control_debounce_seconds": settings.control_debounce_seconds,
            "idle_shutdown_seconds": settings.idle_shutdown_seconds,
            "setup_ap_ssid": settings.setup_ap_ssid,
            "setup_fallback_grace_seconds": settings.setup_fallback_grace_seconds,
            "volume_presets": {
                "low": settings.volume_preset_low_percent,
                "medium": settings.volume_preset_medium_percent,
                "high": settings.volume_preset_high_percent,
            },
        },
        "idle": idle_status,
    }


def _dependency_status_payload(status: DependencyStatus) -> dict[str, object]:
    return {
        "code": status.code,
        "ready": status.ready,
        "message": status.message,
        "reason_code": status.reason_code,
        "backend": status.backend,
        "device_name": status.device_name,
        "source": status.source,
    }
