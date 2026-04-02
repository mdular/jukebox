"""Tests for shared feedback-state tracking."""

from __future__ import annotations

import unittest

from jukebox.core.models import ControllerEvent
from jukebox.feedback_state import FeedbackStateTracker


class FeedbackStateTrackerTests(unittest.TestCase):
    def test_tracker_updates_snapshot_for_setup_and_action_events(self) -> None:
        tracker = FeedbackStateTracker()

        tracker.handle(
            ControllerEvent(code="setup_required", message="setup required", setup_mode="setup_ap")
        )
        tracker.handle(
            ControllerEvent(
                code="action_succeeded",
                message="playback mode set to queue_tracks",
                action_name="mode.queue",
                playback_mode="queue_tracks",
            )
        )

        snapshot = tracker.snapshot()
        self.assertEqual(snapshot.display_state, "action_succeeded")
        self.assertEqual(snapshot.setup_mode, "setup_ap")
        self.assertEqual(snapshot.playback_mode, "queue_tracks")
        self.assertEqual(snapshot.action_name, "mode.queue")
