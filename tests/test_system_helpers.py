"""Tests for privileged helper command execution."""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from jukebox.adapters.system_helpers import CommandSystemHelpers


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


def _completed(*, stdout: str = "", stderr: str = "", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)
