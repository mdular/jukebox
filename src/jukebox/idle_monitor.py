"""Idle shutdown monitoring."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from .core.models import ControllerEvent, EventSink

Clock = Callable[[], float]
ShutdownCallback = Callable[[str], object]
PlayerActive = Callable[[], bool | None]


class IdleMonitor(EventSink):
    """Track recent activity and request shutdown after long idle."""

    def __init__(
        self,
        *,
        idle_shutdown_seconds: float | None,
        player_active: PlayerActive,
        shutdown_callback: ShutdownCallback,
        poll_interval_seconds: float = 1.0,
        clock: Clock | None = None,
    ) -> None:
        self._idle_shutdown_seconds = idle_shutdown_seconds
        self._player_active = player_active
        self._shutdown_callback = shutdown_callback
        self._poll_interval_seconds = poll_interval_seconds
        self._clock = time.monotonic if clock is None else clock
        self._last_activity = self._clock()
        self._setup_mode_active = False
        self._shutdown_requested = False
        self._event_sinks: list[EventSink] = []
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def bind_event_sinks(self, event_sinks: list[EventSink]) -> None:
        """Provide the sinks used for background auto-shutdown events."""

        self._event_sinks = list(event_sinks)

    def start(self) -> None:
        """Start the background idle poller when idle shutdown is enabled."""

        if self._idle_shutdown_seconds is None:
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        thread = threading.Thread(target=self._run, name="jukebox-idle-monitor", daemon=True)
        self._thread = thread
        thread.start()

    def stop(self) -> None:
        """Stop the background idle poller."""

        self._stop_event.set()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=1.0)

    def handle(self, event: ControllerEvent) -> None:
        """Record meaningful household activity from events."""

        if event.code in {
            "playback_dispatch_succeeded",
            "playback_enqueued",
            "action_succeeded",
            "playback_mode_changed",
        }:
            self._last_activity = self._clock()
        if event.code in {"setup_required", "auth_required"}:
            self._setup_mode_active = True
        elif event.code == "ready":
            self._setup_mode_active = False

    def poll_once(self) -> ControllerEvent | None:
        """Return an auto-shutdown event once the idle timeout is reached."""

        if self._idle_shutdown_seconds is None or self._shutdown_requested:
            return None
        if self._setup_mode_active:
            return None
        player_active = self._player_active()
        if player_active is None or player_active:
            return None
        if (self._clock() - self._last_activity) < self._idle_shutdown_seconds:
            return None

        self._shutdown_requested = True
        self._shutdown_callback("idle")
        return ControllerEvent(
            code="auto_shutdown_requested",
            message="idle shutdown requested",
            action_scope="operator",
        )

    def status(self) -> dict[str, object]:
        """Return diagnostic idle-monitor state."""

        return {
            "enabled": self._idle_shutdown_seconds is not None,
            "timeout_seconds": self._idle_shutdown_seconds,
            "setup_mode_active": self._setup_mode_active,
            "shutdown_requested": self._shutdown_requested,
            "last_activity_age_seconds": round(self._clock() - self._last_activity, 1),
        }

    def _run(self) -> None:
        while not self._stop_event.wait(self._poll_interval_seconds):
            event = self.poll_once()
            if event is not None:
                self._emit(event)

    def _emit(self, event: ControllerEvent) -> None:
        for sink in self._event_sinks:
            if sink is self:
                continue
            sink.handle(event)
