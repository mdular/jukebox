"""Tests for runtime dependency health supervision."""

from __future__ import annotations

import unittest

from jukebox.runtime_health import DependencyStatus, RuntimeHealthMonitor


class RuntimeHealthMonitorTests(unittest.TestCase):
    def test_priority_order_prefers_highest_priority_degraded_status(self) -> None:
        cases = (
            (
                "scanner_unavailable",
                _MutableStatusSource(
                    _status(
                        code="scanner_unavailable",
                        ready=False,
                        message="Scanner unavailable.",
                        reason_code="scanner_unavailable",
                        source="evdev",
                    )
                ),
                _MutableStatusSource(
                    _status(
                        code="controller_auth_unavailable",
                        ready=False,
                        message="Spotify controller auth unavailable.",
                        reason_code="spotify_api_auth_error",
                        backend="spotify",
                    )
                ),
            ),
            (
                "controller_auth_unavailable",
                _MutableStatusSource(_status()),
                _MutableStatusSource(
                    _status(
                        code="controller_auth_unavailable",
                        ready=False,
                        message="Spotify controller auth unavailable.",
                        reason_code="spotify_api_auth_error",
                        backend="spotify",
                    )
                ),
            ),
            (
                "network_unavailable",
                _MutableStatusSource(_status()),
                _MutableStatusSource(
                    _status(
                        code="network_unavailable",
                        ready=False,
                        message="Spotify network discovery unavailable.",
                        reason_code="network_discovery_failed",
                        backend="spotify",
                    )
                ),
            ),
            (
                "receiver_unavailable",
                _MutableStatusSource(_status()),
                _MutableStatusSource(
                    _status(
                        code="receiver_unavailable",
                        ready=False,
                        message="Spotify target device unavailable.",
                        reason_code="device_not_listed",
                        backend="spotify",
                        device_name="jukebox",
                    )
                ),
            ),
        )

        for expected_code, scanner_status, playback_status in cases:
            with self.subTest(expected_code=expected_code):
                monitor = RuntimeHealthMonitor(
                    scanner_status=scanner_status.status,
                    playback_status=playback_status.status,
                    poll_interval_seconds=5.0,
                    source="evdev",
                )

                event = monitor.poll_once()

                self.assertIsNotNone(event)
                assert event is not None
                self.assertEqual(event.code, expected_code)

    def test_ready_is_reemitted_after_recovery_but_duplicate_states_are_suppressed(self) -> None:
        scanner_status = _MutableStatusSource(
            _status(
                code="scanner_unavailable",
                ready=False,
                message="Scanner unavailable.",
                reason_code="scanner_unavailable",
                source="evdev",
            )
        )
        playback_status = _MutableStatusSource(_status(backend="spotify", device_name="jukebox"))
        monitor = RuntimeHealthMonitor(
            scanner_status=scanner_status.status,
            playback_status=playback_status.status,
            poll_interval_seconds=5.0,
            source="evdev",
        )

        first_event = monitor.poll_once()
        second_event = monitor.poll_once()
        scanner_status.current = _status(source="evdev")
        third_event = monitor.poll_once()
        fourth_event = monitor.poll_once()

        self.assertIsNotNone(first_event)
        assert first_event is not None
        self.assertEqual(first_event.code, "scanner_unavailable")
        self.assertIsNone(second_event)
        self.assertIsNotNone(third_event)
        assert third_event is not None
        self.assertEqual(third_event.code, "ready")
        self.assertEqual(third_event.source, "evdev")
        self.assertIsNone(fourth_event)

    def test_changed_reason_code_triggers_a_new_event(self) -> None:
        scanner_status = _MutableStatusSource(_status(source="evdev"))
        playback_status = _MutableStatusSource(
            _status(
                code="network_unavailable",
                ready=False,
                message="Spotify network discovery unavailable.",
                reason_code="network_discovery_failed",
                backend="spotify",
            )
        )
        monitor = RuntimeHealthMonitor(
            scanner_status=scanner_status.status,
            playback_status=playback_status.status,
            poll_interval_seconds=5.0,
            source="evdev",
        )

        first_event = monitor.poll_once()
        playback_status.current = _status(
            code="network_unavailable",
            ready=False,
            message="Spotify network discovery unavailable.",
            reason_code="spotify_rate_limited",
            backend="spotify",
        )
        second_event = monitor.poll_once()

        self.assertIsNotNone(first_event)
        self.assertIsNotNone(second_event)
        assert second_event is not None
        self.assertEqual(second_event.code, "network_unavailable")
        self.assertEqual(second_event.reason_code, "spotify_rate_limited")

    def test_setup_required_blocks_ready(self) -> None:
        monitor = RuntimeHealthMonitor(
            scanner_status=_MutableStatusSource(_status(source="evdev")).status,
            playback_status=_MutableStatusSource(_status(backend="spotify")).status,
            setup_status=_MutableStatusSource(
                _status(
                    code="setup_required",
                    ready=False,
                    message="setup required",
                    source="setup",
                )
            ).status,
            poll_interval_seconds=5.0,
            source="evdev",
        )

        event = monitor.poll_once()

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.code, "setup_required")

    def test_auth_required_blocks_ready(self) -> None:
        monitor = RuntimeHealthMonitor(
            scanner_status=_MutableStatusSource(_status(source="evdev")).status,
            playback_status=_MutableStatusSource(_status(backend="spotify")).status,
            setup_status=_MutableStatusSource(
                _status(
                    code="auth_required",
                    ready=False,
                    message="auth required",
                    source="setup",
                )
            ).status,
            poll_interval_seconds=5.0,
            source="evdev",
        )

        event = monitor.poll_once()

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.code, "auth_required")


class _MutableStatusSource:
    def __init__(self, current: DependencyStatus) -> None:
        self.current = current

    def status(self) -> DependencyStatus:
        return self.current


def _status(
    *,
    code: str = "ready",
    ready: bool = True,
    message: str = "waiting for scan input",
    reason_code: str | None = None,
    backend: str | None = None,
    device_name: str | None = None,
    source: str | None = None,
) -> DependencyStatus:
    return DependencyStatus(
        code=code,
        ready=ready,
        message=message,
        reason_code=reason_code,
        backend=backend,
        device_name=device_name,
        source=source,
    )
