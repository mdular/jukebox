"""Tests for runtime assembly."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jukebox.config import from_env
from jukebox.idle_monitor import IdleMonitor
from jukebox.operator_server import OperatorHttpServer
from jukebox.runtime import build_runtime


class BuildRuntimeTests(unittest.TestCase):
    def test_build_runtime_registers_idle_monitor_and_rich_status_surface(self) -> None:
        helper = _FakeSystemHelpers()
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = from_env(
                {
                    "JUKEBOX_ENV": "test",
                    "JUKEBOX_IDLE_SHUTDOWN_SECONDS": "300",
                    "JUKEBOX_OPERATOR_HTTP_PORT": "8081",
                    "JUKEBOX_OPERATOR_STATE_PATH": str(Path(temp_dir) / "state.json"),
                }
            )

            with patch("jukebox.runtime.CommandSystemHelpers", return_value=helper):
                runtime = build_runtime(settings, io.StringIO(""))

            self.assertTrue(any(isinstance(service, IdleMonitor) for service in runtime.services))
            self.assertTrue(any(isinstance(sink, IdleMonitor) for sink in runtime.event_sinks))

            operator_server = next(
                service for service in runtime.services if isinstance(service, OperatorHttpServer)
            )
            response = operator_server.handle_request("GET", "/status.json")

            payload = response.json_body
            assert payload is not None
            runtime_payload = payload["runtime"]
            assert isinstance(runtime_payload, dict)
            self.assertIn("enabled_actions", runtime_payload)
            self.assertIn("scanner", runtime_payload)
            self.assertIn("playback", runtime_payload)
            self.assertIn("setup", runtime_payload)
            self.assertIn("config", runtime_payload)
            self.assertIn("idle", runtime_payload)
            config_payload = runtime_payload["config"]
            assert isinstance(config_payload, dict)
            self.assertIn("wifi_rollback_timeout_seconds", config_payload)


class _FakeSystemHelpers:
    def status(self) -> dict[str, bool]:
        return {
            "has_client_config": True,
            "client_connected": True,
            "ap_active": False,
        }

    def start_setup_ap(self) -> tuple[bool, str]:
        return True, "setup ap started"

    def apply_wifi(self, ssid: str, passphrase: str) -> str:
        del ssid, passphrase
        return "saved"

    def start_auth(self) -> dict[str, object]:
        return {"state": "pending"}

    def reset_wifi(self) -> tuple[bool, str]:
        return True, "wifi reset"

    def request_shutdown(self, *, reason: str) -> tuple[bool, str]:
        return True, f"shutdown requested: {reason}"
