"""Tests for terminal feedback rendering."""

import io
import unittest

from jukebox.adapters.feedback import TerminalStatusSink
from jukebox.core.models import ControllerEvent


class TerminalStatusSinkTests(unittest.TestCase):
    def test_renders_controller_auth_and_network_unavailable_events(self) -> None:
        stream = io.StringIO()
        sink = TerminalStatusSink(stream)

        sink.handle(
            ControllerEvent(
                code="controller_auth_unavailable",
                message="Spotify controller auth unavailable.",
                backend="spotify",
                reason_code="spotify_api_auth_error",
            )
        )
        sink.handle(
            ControllerEvent(
                code="network_unavailable",
                message="Spotify network discovery unavailable.",
                backend="spotify",
                reason_code="network_discovery_failed",
            )
        )

        self.assertEqual(
            stream.getvalue().splitlines(),
            [
                "[API AUTH] unavailable: spotify_api_auth_error",
                "[NETWORK] unavailable: network_discovery_failed",
            ],
        )

    def test_renders_setup_auth_and_action_events(self) -> None:
        stream = io.StringIO()
        sink = TerminalStatusSink(stream)

        sink.handle(
            ControllerEvent(
                code="setup_required",
                message="setup required",
                setup_mode="setup_ap",
            )
        )
        sink.handle(
            ControllerEvent(
                code="action_succeeded",
                message="playback mode set to queue_tracks",
                action_name="mode.queue",
            )
        )
        sink.handle(
            ControllerEvent(
                code="playback_enqueued",
                message="queued track",
                backend="spotify",
                uri_kind="track",
            )
        )

        self.assertEqual(
            stream.getvalue().splitlines(),
            [
                "[SETUP] required: setup_ap",
                "[ACTION] mode.queue",
                "[QUEUE spotify] queued track",
            ],
        )
