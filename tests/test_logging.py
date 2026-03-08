"""Tests for logging configuration."""

import io
import json
import logging
import unittest

from jukebox.logging import configure_logging


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
