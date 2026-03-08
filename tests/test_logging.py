"""Tests for logging configuration."""

import io
import json
import logging
import unittest

from jukebox.core.models import ControllerEvent
from jukebox.logging import StructuredEventLogger, configure_logging


class ConfigureLoggingTests(unittest.TestCase):
    def test_json_logging_emits_structured_output(self) -> None:
        stream = io.StringIO()
        configure_logging(level="INFO", log_format="json", environment="test", stream=stream)

        logger = logging.getLogger("jukebox.test.json")
        logger.info("structured output")

        payload = json.loads(stream.getvalue())
        self.assertEqual(payload["environment"], "test")
        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["logger"], "jukebox.test.json")
        self.assertEqual(payload["message"], "structured output")

    def test_console_logging_writes_human_readable_output(self) -> None:
        stream = io.StringIO()
        configure_logging(level="INFO", log_format="console", environment="test", stream=stream)

        logger = logging.getLogger("jukebox.test.console")
        logger.info("console output")

        output = stream.getvalue()
        self.assertIn("INFO", output)
        self.assertIn("jukebox.test.console", output)
        self.assertIn("console output", output)

    def test_structured_event_logging_preserves_event_metadata(self) -> None:
        stream = io.StringIO()
        configure_logging(level="INFO", log_format="json", environment="test", stream=stream)

        event_logger = StructuredEventLogger()
        event_logger.handle(
            ControllerEvent(
                code="playback_dispatch_failed",
                message="Spotify playback failed.",
                payload="spotify:track:6rqhFgbbKwnb9MLmUQDhG6",
                uri_kind="track",
                backend="spotify",
                reason_code="spotify_no_active_device",
                device_name="jukebox",
                source="evdev",
            )
        )

        payload = json.loads(stream.getvalue())
        self.assertEqual(payload["event"], "playback_dispatch_failed")
        self.assertEqual(payload["payload"], "spotify:track:6rqhFgbbKwnb9MLmUQDhG6")
        self.assertEqual(payload["uri_kind"], "track")
        self.assertEqual(payload["backend"], "spotify")
        self.assertEqual(payload["reason_code"], "spotify_no_active_device")
        self.assertEqual(payload["device_name"], "jukebox")
        self.assertEqual(payload["source"], "evdev")
