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

    def test_stub_backend_supports_enqueue_and_control_actions(self) -> None:
        backend = StubPlaybackBackend()
        request = PlaybackRequest(
            uri=SpotifyUri(
                raw="spotify:track:6rqhFgbbKwnb9MLmUQDhG6",
                kind="track",
                spotify_id="6rqhFgbbKwnb9MLmUQDhG6",
            )
        )

        enqueue_result = backend.enqueue(request)
        stop_result = backend.stop()
        next_result = backend.skip_next()
        volume_result = backend.set_volume_percent(65)

        self.assertTrue(enqueue_result.ok)
        self.assertTrue(stop_result.ok)
        self.assertTrue(next_result.ok)
        self.assertTrue(volume_result.ok)

    def test_stub_backend_reports_player_activity(self) -> None:
        backend = StubPlaybackBackend()
        request = PlaybackRequest(
            uri=SpotifyUri(
                raw="spotify:track:6rqhFgbbKwnb9MLmUQDhG6",
                kind="track",
                spotify_id="6rqhFgbbKwnb9MLmUQDhG6",
            )
        )

        self.assertFalse(backend.player_active())
        backend.dispatch(request)
        self.assertTrue(backend.player_active())
        backend.stop()
        self.assertFalse(backend.player_active())
