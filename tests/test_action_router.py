"""Tests for action routing."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jukebox.adapters.action_router import ActionRouter
from jukebox.core.cards import JukeboxActionCard
from jukebox.core.models import PlaybackResult
from jukebox.operator_state import OperatorStateStore


class ActionRouterTests(unittest.TestCase):
    def test_mode_queue_persists_queue_tracks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = OperatorStateStore(Path(temp_dir) / "state.json")
            router = ActionRouter(
                playback_backend=_PlaybackBackend(),
                operator_state=store,
                system_helpers=_SystemHelpers(),
                volume_presets={"low": 35, "medium": 55, "high": 75},
            )

            result = router.execute(_action("mode", "queue"))

            self.assertTrue(result.ok)
            self.assertEqual(result.playback_mode, "queue_tracks")
            self.assertEqual(store.load().playback_mode, "queue_tracks")

    def test_unsupported_action_returns_explicit_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            router = ActionRouter(
                playback_backend=_PlaybackBackend(),
                operator_state=OperatorStateStore(Path(temp_dir) / "state.json"),
                system_helpers=_SystemHelpers(),
                volume_presets={"low": 35, "medium": 55, "high": 75},
            )

            result = router.execute(_action("lights", "blink"))

            self.assertFalse(result.ok)
            self.assertEqual(result.reason_code, "unsupported_action")

    def test_wifi_reset_marks_setup_requested_and_calls_helper(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            helpers = _SystemHelpers()
            store = OperatorStateStore(Path(temp_dir) / "state.json")
            router = ActionRouter(
                playback_backend=_PlaybackBackend(),
                operator_state=store,
                system_helpers=helpers,
                volume_presets={"low": 35, "medium": 55, "high": 75},
            )

            result = router.execute(_action("setup", "wifi-reset"))

            self.assertTrue(result.ok)
            self.assertEqual(result.setup_mode, "setup_ap")
            self.assertEqual(store.load().last_wifi_mode, "setup_ap")
            self.assertEqual(helpers.calls, [("reset_wifi", None)])


def _action(group: str, action: str) -> JukeboxActionCard:
    return JukeboxActionCard(
        raw=f"jukebox:{group}:{action}",
        group=group,
        action=action,
        action_id=f"{group}.{action}",
    )


class _PlaybackBackend:
    def probe(self) -> PlaybackResult:
        return PlaybackResult(ok=True, backend="stub", message="ready")

    def dispatch(self, request) -> PlaybackResult:  # type: ignore[no-untyped-def]
        del request
        return PlaybackResult(ok=True, backend="stub", message="dispatched")

    def enqueue(self, request) -> PlaybackResult:  # type: ignore[no-untyped-def]
        del request
        return PlaybackResult(ok=True, backend="stub", message="queued")

    def stop(self) -> PlaybackResult:
        return PlaybackResult(ok=True, backend="stub", message="stopped")

    def skip_next(self) -> PlaybackResult:
        return PlaybackResult(ok=True, backend="stub", message="skipped")

    def set_volume_percent(self, percent: int) -> PlaybackResult:
        return PlaybackResult(ok=True, backend="stub", message=str(percent))

    def player_active(self) -> bool | None:
        return False


class _SystemHelpers:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def reset_wifi(self) -> tuple[bool, str]:
        self.calls.append(("reset_wifi", None))
        return True, "wifi reset"

    def request_shutdown(self, *, reason: str) -> tuple[bool, str]:
        self.calls.append(("request_shutdown", reason))
        return True, "shutdown requested"
