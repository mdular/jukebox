"""Tests for the stub playback backend."""

import unittest

from jukebox.adapters.playback_stub import StubPlaybackBackend
from jukebox.core.models import PlaybackRequest, SpotifyUri


class StubPlaybackBackendTests(unittest.TestCase):
    def test_stub_backend_returns_successful_dispatch_result(self) -> None:
        backend = StubPlaybackBackend()

        result = backend.dispatch(
            PlaybackRequest(
                uri=SpotifyUri(
                    raw="spotify:track:6rqhFgbbKwnb9MLmUQDhG6",
                    kind="track",
                    spotify_id="6rqhFgbbKwnb9MLmUQDhG6",
                )
            )
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.backend, "stub")
        self.assertIn("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", result.message or "")

    def test_stub_backend_reports_ready_status(self) -> None:
        backend = StubPlaybackBackend()

        status = backend.status()

        self.assertTrue(status.ready)
        self.assertEqual(status.code, "ready")
        self.assertEqual(status.backend, "stub")
