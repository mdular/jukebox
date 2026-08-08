"""Tests for privileged helper command execution."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from jukebox.adapters.system_helpers import CommandSystemHelpers

AUTH_HELPER_PATH = Path("scripts/runtime/jukebox-spotifyd-auth-helper.sh")


class CommandSystemHelpersTests(unittest.TestCase):
    def test_reset_wifi_uses_sudoers_wrapped_helper(self) -> None:
        helper = CommandSystemHelpers(
            wifi_helper_command="/usr/local/libexec/jukebox-wifi-helper",
            spotifyd_auth_helper_command="/usr/local/libexec/jukebox-spotifyd-auth-helper",
            shutdown_helper_command="/usr/local/libexec/jukebox-shutdown-helper",
        )

        with patch("subprocess.run", return_value=_completed(stdout="setup ap started")) as run:
            ok, message = helper.reset_wifi()

        self.assertTrue(ok)
        self.assertEqual(message, "setup ap started")
        run.assert_called_once_with(
            ["sudo", "-n", "/usr/local/libexec/jukebox-wifi-helper", "reset-client"],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_apply_wifi_uses_sudoers_wrapped_helper(self) -> None:
        helper = CommandSystemHelpers(
            wifi_helper_command="/usr/local/libexec/jukebox-wifi-helper",
            spotifyd_auth_helper_command="/usr/local/libexec/jukebox-spotifyd-auth-helper",
            shutdown_helper_command="/usr/local/libexec/jukebox-shutdown-helper",
        )

        with patch(
            "subprocess.run",
            return_value=_completed(stdout=json.dumps({"message": "client applied"})),
        ) as run:
            message = helper.apply_wifi("kids-room", "secret-pass")

        self.assertEqual(message, "client applied")
        run.assert_called_once_with(
            [
                "sudo",
                "-n",
                "/usr/local/libexec/jukebox-wifi-helper",
                "apply-client",
                "kids-room",
                "secret-pass",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_request_shutdown_uses_sudoers_wrapped_helper(self) -> None:
        helper = CommandSystemHelpers(
            wifi_helper_command="/usr/local/libexec/jukebox-wifi-helper",
            spotifyd_auth_helper_command="/usr/local/libexec/jukebox-spotifyd-auth-helper",
            shutdown_helper_command="/usr/local/libexec/jukebox-shutdown-helper",
        )

        with patch("subprocess.run", return_value=_completed(stdout="shutdown requested")) as run:
            ok, message = helper.request_shutdown(reason="action")

        self.assertTrue(ok)
        self.assertEqual(message, "shutdown requested")
        run.assert_called_once_with(
            [
                "sudo",
                "-n",
                "/usr/local/libexec/jukebox-shutdown-helper",
                "--reason",
                "action",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_start_auth_uses_sudoers_wrapped_helper(self) -> None:
        helper = CommandSystemHelpers(
            wifi_helper_command="/usr/local/libexec/jukebox-wifi-helper",
            spotifyd_auth_helper_command="/usr/local/libexec/jukebox-spotifyd-auth-helper",
            shutdown_helper_command="/usr/local/libexec/jukebox-shutdown-helper",
        )

        with patch(
            "subprocess.run",
            return_value=_completed(
                stdout=json.dumps(
                    {
                        "state": "pending",
                        "message": "starting receiver authentication",
                    }
                )
            ),
        ) as run:
            payload = helper.start_auth()

        self.assertEqual(payload["state"], "pending")
        self.assertEqual(payload["message"], "starting receiver authentication")
        run.assert_called_once_with(
            ["sudo", "-n", "/usr/local/libexec/jukebox-spotifyd-auth-helper", "start"],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_auth_status_uses_sudoers_wrapped_helper(self) -> None:
        helper = CommandSystemHelpers(
            wifi_helper_command="/usr/local/libexec/jukebox-wifi-helper",
            spotifyd_auth_helper_command="/usr/local/libexec/jukebox-spotifyd-auth-helper",
            shutdown_helper_command="/usr/local/libexec/jukebox-shutdown-helper",
        )

        with patch(
            "subprocess.run",
            return_value=_completed(
                stdout=json.dumps(
                    {
                        "state": "running",
                        "message": "waiting for Spotify approval",
                    }
                )
            ),
        ) as run:
            payload = helper.auth_status()

        self.assertEqual(payload["state"], "running")
        self.assertEqual(payload["message"], "waiting for Spotify approval")
        run.assert_called_once_with(
            ["sudo", "-n", "/usr/local/libexec/jukebox-spotifyd-auth-helper", "status"],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_status_uses_sudoers_wrapped_helper(self) -> None:
        helper = CommandSystemHelpers(
            wifi_helper_command="/usr/local/libexec/jukebox-wifi-helper",
            spotifyd_auth_helper_command="/usr/local/libexec/jukebox-spotifyd-auth-helper",
            shutdown_helper_command="/usr/local/libexec/jukebox-shutdown-helper",
        )

        with patch(
            "subprocess.run",
            return_value=_completed(
                stdout=json.dumps(
                    {
                        "has_client_config": True,
                        "client_connected": False,
                        "ap_active": False,
                    }
                )
            ),
        ) as run:
            status = helper.status()

        self.assertEqual(
            status,
            {
                "has_client_config": True,
                "client_connected": False,
                "ap_active": False,
            },
        )
        run.assert_called_once_with(
            ["sudo", "-n", "/usr/local/libexec/jukebox-wifi-helper", "status"],
            check=False,
            capture_output=True,
            text=True,
        )


class SpotifydAuthHelperScriptTests(unittest.TestCase):
    def test_status_defaults_to_failed_before_auth_starts(self) -> None:
        with _AuthHelperFixture() as fixture:
            result = fixture.run("status")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = fixture.json_output(result)
            self.assertEqual(payload["state"], "failed")
            self.assertIn("not started", str(payload["message"]))

    def test_start_transitions_pending_to_running_to_succeeded(self) -> None:
        with _AuthHelperFixture() as fixture:
            start_result = fixture.run("start")

            self.assertEqual(start_result.returncode, 0, start_result.stderr)
            self.assertEqual(fixture.json_output(start_result)["state"], "pending")

            running = fixture.wait_for_state("running")
            self.assertEqual(running["state"], "running")

            fixture.release("success")
            succeeded = fixture.wait_for_state("succeeded")
            self.assertEqual(succeeded["state"], "succeeded")
            self.assertIn("completed", str(succeeded["message"]))

    def test_start_transitions_pending_to_running_to_failed(self) -> None:
        with _AuthHelperFixture() as fixture:
            start_result = fixture.run("start")

            self.assertEqual(start_result.returncode, 0, start_result.stderr)
            self.assertEqual(fixture.json_output(start_result)["state"], "pending")

            running = fixture.wait_for_state("running")
            self.assertEqual(running["state"], "running")

            fixture.release("failed")
            failed = fixture.wait_for_state("failed")
            self.assertEqual(failed["state"], "failed")
            self.assertIn("approval failed", str(failed["message"]))

    def test_start_returns_failed_json_when_spotifyd_is_unavailable(self) -> None:
        with _AuthHelperFixture(install_fake_spotifyd=False) as fixture:
            result = fixture.run("start")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = fixture.json_output(result)
            self.assertEqual(payload["state"], "failed")
            self.assertIn("not installed", str(payload["message"]))


def _completed(*, stdout: str = "", stderr: str = "", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


class _AuthHelperFixture:
    def __init__(self, *, install_fake_spotifyd: bool = True) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)
        self.state_dir = self.root / "spotifyd-auth-helper"
        self.continue_path = self.root / "continue"
        self.fake_spotifyd_path = self.root / "fake_spotifyd.py"
        self.install_fake_spotifyd = install_fake_spotifyd

    def __enter__(self) -> _AuthHelperFixture:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if self.install_fake_spotifyd:
            self.fake_spotifyd_path.write_text(_FAKE_SPOTIFYD, encoding="utf-8")
            self.fake_spotifyd_path.chmod(
                stat.S_IRUSR
                | stat.S_IWUSR
                | stat.S_IXUSR
                | stat.S_IRGRP
                | stat.S_IXGRP
            )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if not self.continue_path.exists():
            self.continue_path.write_text("success", encoding="utf-8")
        self._temp_dir.cleanup()

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "JUKEBOX_SPOTIFYD_AUTH_HELPER_STATE_DIR": str(self.state_dir),
                "JUKEBOX_SPOTIFYD_AUTH_COMMAND": str(self.fake_spotifyd_path),
                "FAKE_SPOTIFYD_CONTINUE_PATH": str(self.continue_path),
            }
        )
        return subprocess.run(
            ["/bin/sh", str(AUTH_HELPER_PATH), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
            cwd=Path.cwd(),
        )

    def json_output(self, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        payload = json.loads(result.stdout)
        assert isinstance(payload, dict)
        return payload

    def wait_for_state(
        self,
        expected_state: str,
        *,
        timeout_seconds: float = 3.0,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            payload = self.json_output(self.run("status"))
            if payload.get("state") == expected_state:
                return payload
            time.sleep(0.05)
        raise AssertionError(f"timed out waiting for auth helper state {expected_state!r}")

    def release(self, result: str) -> None:
        self.continue_path.write_text(result, encoding="utf-8")


_FAKE_SPOTIFYD = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import os
    import sys
    import time
    from pathlib import Path

    if sys.argv[1:] != ["authenticate"]:
        raise SystemExit(2)

    continue_path = Path(os.environ["FAKE_SPOTIFYD_CONTINUE_PATH"])
    print("https://example.test/approve", flush=True)
    deadline = time.monotonic() + 5.0
    while not continue_path.exists():
        if time.monotonic() >= deadline:
            print("timed out waiting for approval", file=sys.stderr, flush=True)
            raise SystemExit(3)
        time.sleep(0.05)

    outcome = continue_path.read_text(encoding="utf-8").strip()
    if outcome == "success":
        raise SystemExit(0)

    print("approval failed", file=sys.stderr, flush=True)
    raise SystemExit(1)
    """
)
