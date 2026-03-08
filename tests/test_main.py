"""Smoke tests for the application entrypoint."""

import io
import os
import unittest
from contextlib import redirect_stderr
from unittest import mock

from jukebox.main import main


class MainTests(unittest.TestCase):
    def test_main_returns_zero_and_logs_startup_message(self) -> None:
        stderr_buffer = io.StringIO()

        with mock.patch.dict(os.environ, {}, clear=True):
            with redirect_stderr(stderr_buffer):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertIn("jukebox scaffold initialized", stderr_buffer.getvalue())

    def test_main_returns_nonzero_for_invalid_configuration(self) -> None:
        stderr_buffer = io.StringIO()

        with mock.patch.dict(os.environ, {"JUKEBOX_LOG_FORMAT": "xml"}, clear=True):
            with redirect_stderr(stderr_buffer):
                exit_code = main()

        self.assertEqual(exit_code, 2)
        self.assertIn("Configuration error", stderr_buffer.getvalue())
