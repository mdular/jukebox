"""Tests for controller orchestration."""

import tempfile
import unittest
from pathlib import Path

from jukebox.adapters.action_router import ActionRouter
from jukebox.core.controller import Controller
from jukebox.core.deduper import DuplicateGate
from jukebox.core.models import ControllerEvent, PlaybackRequest, PlaybackResult
from jukebox.operator_state import OperatorStateStore


class ControllerTests(unittest.TestCase):
    def test_valid_scan_is_accepted_and_dispatched(self) -> None:
        sink = _RecordingSink()
        backend = _RecordingBackend(
            [PlaybackResult(ok=True, backend="stub", message="played", device_name="jukebox")]
        )
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
        self.assertEqual(sink.events[-1].device_name, "jukebox")

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

    def test_action_card_is_routed_and_emits_action_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = _RecordingSink()
            backend = _RecordingBackend([])
            controller = Controller(
                playback_backend=backend,
                duplicate_gate=DuplicateGate(window_seconds=2.0, clock=_FakeClock([])),
                action_router=ActionRouter(
                    playback_backend=backend,
                    operator_state=OperatorStateStore(Path(temp_dir) / "state.json"),
                    system_helpers=_SystemHelpers(),
                    volume_presets={"low": 35, "medium": 55, "high": 75},
                ),
                operator_state=OperatorStateStore(Path(temp_dir) / "state.json"),
                event_sinks=[sink],
            )

            controller.process_line("jukebox:mode:queue\n")

            self.assertEqual(
                [event.code for event in sink.events],
                [
                    "scan_received",
                    "action_card_accepted",
                    "action_succeeded",
                    "playback_mode_changed",
                ],
            )
            self.assertEqual(backend.requests, [])

    def test_track_scan_uses_queue_backend_when_playback_mode_is_queue_tracks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = _RecordingSink()
            backend = _RecordingBackend([PlaybackResult(ok=True, backend="stub", message="queued")])
            store = OperatorStateStore(Path(temp_dir) / "state.json")
            store.set_playback_mode("queue_tracks")
            controller = Controller(
                playback_backend=backend,
                duplicate_gate=DuplicateGate(window_seconds=2.0, clock=_FakeClock([10.0])),
                action_router=ActionRouter(
                    playback_backend=backend,
                    operator_state=store,
                    system_helpers=_SystemHelpers(),
                    volume_presets={"low": 35, "medium": 55, "high": 75},
                ),
                operator_state=store,
                event_sinks=[sink],
            )

            controller.process_line("spotify:track:6rqhFgbbKwnb9MLmUQDhG6\n")

            self.assertEqual(backend.enqueued[0].uri.kind, "track")
            self.assertEqual(sink.events[-1].code, "playback_enqueued")

    def test_queue_mode_falls_back_to_replace_for_album_cards(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = _RecordingSink()
            backend = _RecordingBackend([PlaybackResult(ok=True, backend="stub", message="played")])
            store = OperatorStateStore(Path(temp_dir) / "state.json")
            store.set_playback_mode("queue_tracks")
            controller = Controller(
                playback_backend=backend,
                duplicate_gate=DuplicateGate(window_seconds=2.0, clock=_FakeClock([10.0])),
                action_router=ActionRouter(
                    playback_backend=backend,
                    operator_state=store,
                    system_helpers=_SystemHelpers(),
                    volume_presets={"low": 35, "medium": 55, "high": 75},
                ),
                operator_state=store,
                event_sinks=[sink],
            )

            controller.process_line("spotify:album:1ATL5GLyefJaxhQzSPVrLX\n")

            self.assertEqual(len(backend.requests), 1)
            self.assertEqual(
                [event.code for event in sink.events[-3:]],
                ["scan_accepted", "playback_mode_fallback", "playback_dispatch_succeeded"],
            )


class _RecordingBackend:
    def __init__(self, results: list[PlaybackResult]) -> None:
        self._results = results
        self.requests: list[PlaybackRequest] = []
        self.enqueued: list[PlaybackRequest] = []

    def probe(self) -> PlaybackResult:
        return PlaybackResult(ok=True, backend="stub", message="ready")

    def dispatch(self, request: PlaybackRequest) -> PlaybackResult:
        self.requests.append(request)
        if self._results:
            return self._results.pop(0)
        return PlaybackResult(ok=True, backend="stub", message="played")

    def enqueue(self, request: PlaybackRequest) -> PlaybackResult:
        self.enqueued.append(request)
        if self._results:
            return self._results.pop(0)
        return PlaybackResult(ok=True, backend="stub", message="queued")

    def stop(self) -> PlaybackResult:
        return PlaybackResult(ok=True, backend="stub", message="stopped")

    def skip_next(self) -> PlaybackResult:
        return PlaybackResult(ok=True, backend="stub", message="skipped")

    def set_volume_percent(self, percent: int) -> PlaybackResult:
        return PlaybackResult(ok=True, backend="stub", message=str(percent))


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


class _SystemHelpers:
    def reset_wifi(self) -> tuple[bool, str]:
        return True, "wifi reset"

    def request_shutdown(self, *, reason: str) -> tuple[bool, str]:
        return True, f"shutdown requested: {reason}"
