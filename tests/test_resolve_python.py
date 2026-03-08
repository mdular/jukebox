"""Tests for the Python interpreter resolver script."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESOLVER = PROJECT_ROOT / "scripts" / "resolve-python.sh"


def _write_fake_python(directory: Path, name: str, *, version: str, supported: bool) -> Path:
    script = directory / name
    exit_code = "0" if supported else "1"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!/bin/sh
            if [ "${{1:-}}" = "--version" ]; then
              printf '%s\\n' "{version}"
            fi
            exit {exit_code}
            """
        ),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script


class ResolvePythonTests(unittest.TestCase):
    def test_auto_detection_prefers_supported_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            _write_fake_python(temp_dir, "python3", version="Python 3.9.6", supported=False)
            _write_fake_python(temp_dir, "python3.11", version="Python 3.11.9", supported=True)

            result = subprocess.run(
                [str(RESOLVER)],
                capture_output=True,
                check=False,
                env={"PATH": str(temp_dir)},
                text=True,
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "python3.11")

    def test_explicit_python_failure_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            _write_fake_python(temp_dir, "python3.9", version="Python 3.9.6", supported=False)

            result = subprocess.run(
                [str(RESOLVER)],
                capture_output=True,
                check=False,
                env={"PATH": str(temp_dir), "PYTHON": "python3.9"},
                text=True,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Jukebox requires Python 3.11+.", result.stderr)
        self.assertIn("PYTHON=/path/to/python3.11 make venv", result.stderr)

    def test_explicit_python_path_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            python_path = _write_fake_python(
                temp_dir,
                "python-custom",
                version="Python 3.12.1",
                supported=True,
            )

            result = subprocess.run(
                [str(RESOLVER)],
                capture_output=True,
                check=False,
                env={"PATH": os.environ["PATH"], "PYTHON": str(python_path)},
                text=True,
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), str(python_path))
