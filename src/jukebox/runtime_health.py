"""Runtime dependency health supervision."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Iterable, Protocol

from .core.models import ControllerEvent, EventSink

_STATUS_PRIORITY = {
    "scanner_unavailable": 0,
    "setup_required": 1,
    "auth_required": 2,
    "controller_auth_unavailable": 3,
    "network_unavailable": 4,
    "receiver_unavailable": 5,
    "ready": 6,
}


@dataclass(frozen=True)
class DependencyStatus:
    """One dependency health result used to derive runtime readiness."""

    code: str
    ready: bool
    message: str
    reason_code: str | None = None
    backend: str | None = None
    device_name: str | None = None
    source: str | None = None


class HealthMonitor(Protocol):
    """Lifecycle contract for long-running health supervision."""

    def start(self, event_sinks: Iterable[EventSink]) -> None:
        """Start monitoring and emit transitions to the supplied sinks."""

    def stop(self) -> None:
        """Stop monitoring and release any background resources."""


class RuntimeHealthMonitor:
    """Poll scanner and playback dependency health and emit state transitions."""

    def __init__(
        self,
        *,
        scanner_status: Callable[[], DependencyStatus],
        playback_status: Callable[[], DependencyStatus],
        setup_status: Callable[[], DependencyStatus] | None = None,
        poll_interval_seconds: float,
        source: str | None = None,
    ) -> None:
        self._scanner_status = scanner_status
        self._playback_status = playback_status
        self._setup_status = setup_status
        self._poll_interval_seconds = poll_interval_seconds
        self._source = source
        self._lock = threading.Lock()
        self._last_status: DependencyStatus | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._event_sinks: list[EventSink] = []

    def poll_once(self) -> ControllerEvent | None:
        """Poll once and return the next observable event, if any."""

        status = self._current_status()
        with self._lock:
            if self._last_status == status:
                return None
            self._last_status = status
        return ControllerEvent(
            code=status.code,
            message=status.message,
            backend=status.backend,
            reason_code=status.reason_code,
            device_name=status.device_name,
            source=status.source if status.source is not None else self._source,
        )

    def start(self, event_sinks: Iterable[EventSink]) -> None:
        """Start a background polling loop after emitting the initial state."""

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._event_sinks = list(event_sinks)
            self._stop_event.clear()

        initial_event = self.poll_once()
        if initial_event is not None:
            self._emit(initial_event)

        thread = threading.Thread(target=self._run, name="jukebox-runtime-health", daemon=True)
        with self._lock:
            self._thread = thread
        thread.start()

    def stop(self) -> None:
        """Stop the background polling loop."""

        self._stop_event.set()
        with self._lock:
            thread = self._thread
            self._thread = None
        if thread is not None:
            thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop_event.wait(self._poll_interval_seconds):
            event = self.poll_once()
            if event is not None:
                self._emit(event)

    def _emit(self, event: ControllerEvent) -> None:
        with self._lock:
            sinks = list(self._event_sinks)
        for sink in sinks:
            sink.handle(event)

    def _current_status(self) -> DependencyStatus:
        scanner_status = self._scanner_status()
        playback_status = self._playback_status()
        statuses = [scanner_status, playback_status]
        if self._setup_status is not None:
            statuses.append(self._setup_status())
        degraded = [status for status in statuses if not status.ready]
        if not degraded:
            return DependencyStatus(
                code="ready",
                ready=True,
                message="waiting for scan input",
                source=self._source,
            )
        return min(
            degraded,
            key=lambda status: _STATUS_PRIORITY.get(status.code, len(_STATUS_PRIORITY)),
        )
