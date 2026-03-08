"""Tests for controller orchestration."""

import unittest

from jukebox.core.controller import Controller
from jukebox.core.deduper import DuplicateGate
from jukebox.core.models import ControllerEvent, PlaybackRequest, PlaybackResult


class ControllerTests(unittest.TestCase):
    def test_valid_scan_is_accepted_and_dispatched(self) -> None:
        sink = _RecordingSink()
        backend = _RecordingBackend([PlaybackResult(ok=True, backend="stub", message="played")])
        controller = Controller(
            playback_backend=backend,
            duplicate_gate=DuplicateGate(window_seconds=2.0, clock=_FakeClock([10.0])),
            event_sinks=[sink],
        )

        controller.process_line("spotify:track:6rqhFgbbKwnb9MLmUQDhG6\n")

        self.assertEqual(
            [event.code for event in sink.events],
            ["scan_received", "scan_accepted", "playback_dispatch_succeeded"],
        )
        self.assertEqual(backend.requests[0].uri.kind, "track")

    def test_invalid_payload_emits_error_and_does_not_dispatch(self) -> None:
        sink = _RecordingSink()
        backend = _RecordingBackend([])
        controller = Controller(
            playback_backend=backend,
            duplicate_gate=DuplicateGate(window_seconds=2.0, clock=_FakeClock([])),
            event_sinks=[sink],
        )

        controller.process_line("not-a-spotify-uri\n")

        self.assertEqual(
            [event.code for event in sink.events],
            ["scan_received", "invalid_payload"],
        )
        self.assertEqual(backend.requests, [])

    def test_unsupported_spotify_uri_emits_unsupported_content(self) -> None:
        sink = _RecordingSink()
        backend = _RecordingBackend([])
        controller = Controller(
            playback_backend=backend,
            duplicate_gate=DuplicateGate(window_seconds=2.0, clock=_FakeClock([])),
            event_sinks=[sink],
        )

        controller.process_line("spotify:artist:4gzpq5DPGxSnKTe4SA8HAU\n")

        self.assertEqual(
            [event.code for event in sink.events],
            ["scan_received", "unsupported_content"],
        )

    def test_duplicate_scan_is_suppressed_after_success(self) -> None:
        sink = _RecordingSink()
        backend = _RecordingBackend(
            [
                PlaybackResult(ok=True, backend="stub", message="played"),
            ]
        )
        controller = Controller(
            playback_backend=backend,
            duplicate_gate=DuplicateGate(window_seconds=2.0, clock=_FakeClock([10.0, 11.0])),
            event_sinks=[sink],
        )

        controller.process_line("spotify:track:6rqhFgbbKwnb9MLmUQDhG6\n")
        controller.process_line("spotify:track:6rqhFgbbKwnb9MLmUQDhG6\n")

        self.assertEqual(len(backend.requests), 1)
        self.assertEqual(sink.events[-1].code, "duplicate_suppressed")

    def test_failed_dispatch_does_not_record_duplicate_state(self) -> None:
        sink = _RecordingSink()
        backend = _RecordingBackend(
            [
                PlaybackResult(
                    ok=False,
                    backend="spotify",
                    reason_code="spotify_no_active_device",
                    message="No active device.",
                ),
                PlaybackResult(ok=True, backend="spotify", message="played"),
            ]
        )
        controller = Controller(
            playback_backend=backend,
            duplicate_gate=DuplicateGate(window_seconds=2.0, clock=_FakeClock([10.0, 10.1])),
            event_sinks=[sink],
        )

        controller.process_line("spotify:track:6rqhFgbbKwnb9MLmUQDhG6\n")
        controller.process_line("spotify:track:6rqhFgbbKwnb9MLmUQDhG6\n")

        self.assertEqual(len(backend.requests), 2)
        self.assertEqual(
            [event.code for event in sink.events],
            [
                "scan_received",
                "scan_accepted",
                "playback_dispatch_failed",
                "scan_received",
                "scan_accepted",
                "playback_dispatch_succeeded",
            ],
        )

    def test_empty_lines_are_ignored(self) -> None:
        sink = _RecordingSink()
        controller = Controller(
            playback_backend=_RecordingBackend([]),
            duplicate_gate=DuplicateGate(window_seconds=2.0, clock=_FakeClock([])),
            event_sinks=[sink],
        )

        controller.process_line("\n")

        self.assertEqual(sink.events, [])

    def test_emit_idle_outputs_idle_event(self) -> None:
        sink = _RecordingSink()
        controller = Controller(
            playback_backend=_RecordingBackend([]),
            duplicate_gate=DuplicateGate(window_seconds=2.0, clock=_FakeClock([])),
            event_sinks=[sink],
        )

        controller.emit_idle()

        self.assertEqual([event.code for event in sink.events], ["idle"])


class _RecordingBackend:
    def __init__(self, results: list[PlaybackResult]) -> None:
        self._results = results
        self.requests: list[PlaybackRequest] = []

    def dispatch(self, request: PlaybackRequest) -> PlaybackResult:
        self.requests.append(request)
        if self._results:
            return self._results.pop(0)
        return PlaybackResult(ok=True, backend="stub", message="played")


class _RecordingSink:
    def __init__(self) -> None:
        self.events: list[ControllerEvent] = []

    def handle(self, event: ControllerEvent) -> None:
        self.events.append(event)


class _FakeClock:
    def __init__(self, values: list[float]) -> None:
        self._values = values

    def __call__(self) -> float:
        return self._values.pop(0)
