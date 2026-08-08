"""Tests for operator-state persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jukebox.operator_state import OperatorState, OperatorStateStore


class OperatorStateStoreTests(unittest.TestCase):
    def test_missing_state_file_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            store = OperatorStateStore(path)

            state = store.load()

            self.assertEqual(state.playback_mode, "replace")
            self.assertFalse(state.setup_requested)
            self.assertFalse(state.receiver_reauth_requested)
            self.assertFalse(state.receiver_reauth_started)
            self.assertIn("system.shutdown", state.enabled_actions)

    def test_save_persists_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            store = OperatorStateStore(path)

            store.save(
                OperatorState(
                    playback_mode="queue_tracks",
                    setup_requested=True,
                    receiver_reauth_requested=False,
                    receiver_reauth_started=False,
                    last_wifi_mode="setup_ap",
                    enabled_actions=frozenset({"playback.stop", "mode.queue"}),
                )
            )

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["playback_mode"], "queue_tracks")
            self.assertTrue(payload["setup_requested"])
            self.assertFalse(payload["receiver_reauth_started"])
            self.assertEqual(payload["last_wifi_mode"], "setup_ap")
            self.assertEqual(payload["enabled_actions"], ["mode.queue", "playback.stop"])

    def test_corrupt_state_file_resets_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            path.write_text("{not-json", encoding="utf-8")
            store = OperatorStateStore(path)

            state = store.load()

            self.assertEqual(state.playback_mode, "replace")
            repaired_payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(repaired_payload["schema_version"], 2)

    def test_reauth_attempt_lifecycle_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = OperatorStateStore(Path(temp_dir) / "state.json")

            requested = store.mark_receiver_reauth_requested(True)
            started = store.mark_receiver_reauth_started()
            repeated_request = store.mark_receiver_reauth_requested(True)
            completed = store.mark_receiver_reauth_requested(False)

            self.assertTrue(requested.receiver_reauth_requested)
            self.assertFalse(requested.receiver_reauth_started)
            self.assertTrue(started.receiver_reauth_started)
            self.assertTrue(repeated_request.receiver_reauth_started)
            self.assertFalse(completed.receiver_reauth_requested)
            self.assertFalse(completed.receiver_reauth_started)
