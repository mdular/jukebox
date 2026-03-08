"""Smoke tests for the application entrypoint."""

import io
import unittest
from pathlib import Path

from jukebox.main import main


class MainTests(unittest.TestCase):
    def test_main_runs_controller_until_eof(self) -> None:
        fixture_path = Path("tests/fixtures/scan_streams/happy_path.txt")
        stdin_buffer = io.StringIO(fixture_path.read_text(encoding="utf-8"))
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        exit_code = main(
            stdin=stdin_buffer,
            stdout=stdout_buffer,
            stderr=stderr_buffer,
            env={"JUKEBOX_ENV": "test"},
        )

        self.assertEqual(exit_code, 0)
        output = stdout_buffer.getvalue()
        self.assertIn("[IDLE] waiting for scan input", output)
        self.assertIn("[ACCEPTED] track spotify:track:6rqhFgbbKwnb9MLmUQDhG6", output)
        self.assertIn("[DUPLICATE] ignored within 2.0s", output)
        self.assertIn("[ERROR invalid_uri]", output)
        self.assertIn("[ERROR unsupported_content]", output)

    def test_main_returns_nonzero_for_invalid_configuration(self) -> None:
        stderr_buffer = io.StringIO()

        exit_code = main(
            stderr=stderr_buffer,
            env={"JUKEBOX_LOG_FORMAT": "xml"},
        )

        self.assertEqual(exit_code, 2)
        self.assertIn("Configuration error", stderr_buffer.getvalue())

    def test_main_returns_130_for_keyboard_interrupt(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        exit_code = main(
            stdin=_InterruptingInput(),
            stdout=stdout_buffer,
            stderr=stderr_buffer,
            env={"JUKEBOX_ENV": "test"},
        )

        self.assertEqual(exit_code, 130)
        self.assertIn("[IDLE] waiting for scan input", stdout_buffer.getvalue())


class _InterruptingInput:
    def readline(self) -> str:
        raise KeyboardInterrupt
