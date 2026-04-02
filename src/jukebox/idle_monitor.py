"""Idle shutdown monitoring."""

from __future__ import annotations

import time
from collections.abc import Callable

from .core.models import ControllerEvent

Clock = Callable[[], float]
ShutdownCallback = Callable[[str], None]
PlayerActive = Callable[[], bool]


class IdleMonitor:
    """Track recent activity and request shutdown after long idle."""

    def __init__(
        self,
        *,
        idle_shutdown_seconds: float | None,
        player_active: PlayerActive,
        shutdown_callback: ShutdownCallback,
        clock: Clock | None = None,
    ) -> None:
        self._idle_shutdown_seconds = idle_shutdown_seconds
        self._player_active = player_active
        self._shutdown_callback = shutdown_callback
        self._clock = time.monotonic if clock is None else clock
        self._last_activity = self._clock()
        self._shutdown_requested = False

    def start(self) -> None:
        """Satisfy the runtime service lifecycle."""

    def stop(self) -> None:
        """Satisfy the runtime service lifecycle."""

    def handle(self, event: ControllerEvent) -> None:
        """Record meaningful household activity from events."""

        if event.code in {
            "playback_dispatch_succeeded",
            "playback_enqueued",
            "action_succeeded",
            "playback_mode_changed",
        }:
            self._last_activity = self._clock()

    def poll_once(self) -> ControllerEvent | None:
        """Return an auto-shutdown event once the idle timeout is reached."""

        if self._idle_shutdown_seconds is None or self._shutdown_requested:
            return None
        if self._player_active():
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
