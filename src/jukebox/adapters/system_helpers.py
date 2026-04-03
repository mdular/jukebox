"""Helper command adapters for privileged maintenance actions."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, cast


@dataclass
class CommandSystemHelpers:
    """Invoke runtime helper commands through narrow subprocess boundaries."""

    wifi_helper_command: str
    spotifyd_auth_helper_command: str
    shutdown_helper_command: str

    def status(self) -> dict[str, bool]:
        payload = self._run_json(*self._privileged_command(self.wifi_helper_command, "status"))
        return {
            "has_client_config": bool(payload.get("has_client_config", True)),
            "client_connected": bool(payload.get("client_connected", True)),
            "ap_active": bool(payload.get("ap_active", False)),
        }

    def start_setup_ap(self) -> tuple[bool, str]:
        return self._run_status(*self._privileged_command(self.wifi_helper_command, "start-ap"))

    def apply_wifi(self, ssid: str, passphrase: str) -> str:
        payload = self._run_json(
            *self._privileged_command(
                self.wifi_helper_command,
                "apply-client",
                ssid,
                passphrase,
            )
        )
        return str(payload.get("message", "wifi settings applied"))

    def reset_wifi(self) -> tuple[bool, str]:
        return self._run_status(
            *self._privileged_command(self.wifi_helper_command, "reset-client")
        )

    def start_auth(self) -> dict[str, object]:
        return self._run_json(
            *self._privileged_command(self.spotifyd_auth_helper_command, "start")
        )

    def request_shutdown(self, *, reason: str) -> tuple[bool, str]:
        return self._run_status(
            *self._privileged_command(self.shutdown_helper_command, "--reason", reason)
        )

    def _privileged_command(self, command: str, *args: str) -> tuple[str, ...]:
        return ("sudo", "-n", command, *args)

    def _run_status(self, *command: str) -> tuple[bool, str]:
        try:
            completed = subprocess.run(
                list(command),
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            return False, str(exc)
        if completed.returncode != 0:
            return False, (completed.stderr or completed.stdout or "helper failed").strip()
        message = (completed.stdout or "ok").strip()
        return True, message or "ok"

    def _run_json(self, *command: str) -> dict[str, Any]:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "helper failed").strip())
        if completed.stdout.strip() == "":
            return {}
        payload = json.loads(completed.stdout)
        if not isinstance(payload, dict):
            raise RuntimeError("helper did not return a JSON object")
        return cast(dict[str, Any], payload)
