"""Tests for idle shutdown monitoring."""

from __future__ import annotations

import unittest

from jukebox.core.models import ControllerEvent
from jukebox.idle_monitor import IdleMonitor


class IdleMonitorTests(unittest.TestCase):
    def test_poll_once_requests_shutdown_after_idle_timeout(self) -> None:
        requested: list[str] = []
        clock = _FakeClock([0.0, 0.0, 10.0])
        monitor = IdleMonitor(
            idle_shutdown_seconds=5.0,
            player_active=lambda: False,
            shutdown_callback=lambda reason: requested.append(reason),
            clock=clock,
        )

        monitor.handle(ControllerEvent(code="playback_dispatch_succeeded", message="played"))
        event = monitor.poll_once()

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.code, "auto_shutdown_requested")
        self.assertEqual(requested, ["idle"])

    def test_poll_once_does_not_shutdown_while_playback_is_active(self) -> None:
        monitor = IdleMonitor(
            idle_shutdown_seconds=5.0,
            player_active=lambda: True,
            shutdown_callback=lambda reason: None,
            clock=_FakeClock([0.0, 0.0, 10.0]),
        )

        monitor.handle(ControllerEvent(code="playback_dispatch_succeeded", message="played"))

        self.assertIsNone(monitor.poll_once())

    def test_poll_once_does_not_shutdown_while_setup_mode_is_active(self) -> None:
        requested: list[str] = []
        monitor = IdleMonitor(
            idle_shutdown_seconds=5.0,
            player_active=lambda: False,
            shutdown_callback=lambda reason: requested.append(reason),
            clock=_FakeClock([0.0, 0.0, 10.0]),
        )

        monitor.handle(ControllerEvent(code="setup_required", message="setup required"))

        self.assertIsNone(monitor.poll_once())
        self.assertEqual(requested, [])


class _FakeClock:
    def __init__(self, values: list[float]) -> None:
        self._values = values
        self._last = values[-1]

    def __call__(self) -> float:
        if not self._values:
            return self._last
        self._last = self._values.pop(0)
        return self._last
