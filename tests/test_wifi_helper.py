"""Integration-style tests for the Wi-Fi helper script."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Any

HELPER_PATH = Path("scripts/runtime/jukebox-wifi-helper.sh")
NmState = dict[str, Any]


class WifiHelperScriptTests(unittest.TestCase):
    def test_reset_client_starts_ap_and_arms_rollback_when_client_was_working(self) -> None:
        with _Fixture() as fixture:
            fixture.write_nm_state(
                {
                    "connections": [
                        {
                            "name": "home",
                            "type": "802-11-wireless",
                            "mode": "client",
                            "ssid": "Home",
                            "active": True,
                        }
                    ]
                }
            )

            result = fixture.run("reset-client")

            self.assertEqual(result.returncode, 0, result.stderr)
            state = fixture.read_nm_state()
            self.assertEqual(state["active_connection"], "jukebox-setup-ap")
            self.assertTrue(fixture.pending_path.exists())
            pending = fixture.pending_path.read_text(encoding="utf-8")
            self.assertIn("PREVIOUS_CONNECTION_NAME='home'", pending)

    def test_apply_client_commits_new_connection_and_clears_pending_state(self) -> None:
        with _Fixture() as fixture:
            fixture.write_nm_state(
                {
                    "connections": [
                        {
                            "name": "home",
                            "type": "802-11-wireless",
                            "mode": "client",
                            "ssid": "Home",
                            "active": True,
                        }
                    ]
                }
            )
            fixture.run("reset-client").check_returncode()

            result = fixture.run("apply-client", "Kids Room", "secret-pass")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("message", payload)
            active = fixture.active_connection()
            assert active is not None
            self.assertEqual(active["mode"], "client")
            self.assertEqual(active["ssid"], "Kids Room")
            self.assertFalse(fixture.pending_path.exists())

    def test_status_restores_previous_connection_after_reboot_when_trial_pending(self) -> None:
        with _Fixture() as fixture:
            fixture.write_nm_state(
                {
                    "connections": [
                        {
                            "name": "home",
                            "type": "802-11-wireless",
                            "mode": "client",
                            "ssid": "Home",
                            "active": True,
                        }
                    ]
                }
            )
            fixture.run("reset-client").check_returncode()
            fixture.boot_id_path.write_text("boot-b", encoding="utf-8")

            result = fixture.run("status")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["has_client_config"])
            self.assertTrue(payload["client_connected"])
            self.assertFalse(payload["ap_active"])
            self.assertFalse(fixture.pending_path.exists())
            active = fixture.active_connection()
            assert active is not None
            self.assertEqual(active["name"], "home")

    def test_reset_client_without_working_connection_does_not_arm_rollback(self) -> None:
        with _Fixture() as fixture:
            fixture.write_nm_state({"connections": []})

            result = fixture.run("reset-client")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(fixture.run("status").stdout)
            self.assertFalse(payload["has_client_config"])
            self.assertTrue(payload["ap_active"])
            self.assertFalse(fixture.pending_path.exists())


class _Fixture:
    def __init__(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)
        self.nm_state_path = self.root / "nm-state.json"
        self.pending_path = self.root / "wifi-helper" / "pending-trial.env"
        self.boot_id_path = self.root / "boot-id"
        self.fake_nmcli_path = self.root / "fake_nmcli.py"

    def __enter__(self) -> _Fixture:
        self.write_nm_state({"connections": []})
        self.boot_id_path.write_text("boot-a", encoding="utf-8")
        self.fake_nmcli_path.write_text(_FAKE_NMCLI, encoding="utf-8")
        self.fake_nmcli_path.chmod(
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self._temp_dir.cleanup()

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "JUKEBOX_SETUP_AP_SSID": "jukebox-setup",
                "JUKEBOX_SETUP_AP_PASSPHRASE": "setup-pass",
                "JUKEBOX_WIFI_ROLLBACK_TIMEOUT_SECONDS": "120",
                "JUKEBOX_WIFI_HELPER_STATE_DIR": str(self.root / "wifi-helper"),
                "JUKEBOX_WIFI_BOOT_ID_FILE": str(self.boot_id_path),
                "JUKEBOX_WIFI_NMCLI_COMMAND": str(self.fake_nmcli_path),
                "JUKEBOX_WIFI_INTERFACE": "wlan0",
                "JUKEBOX_WIFI_HELPER_DISABLE_BACKGROUND": "1",
                "FAKE_NMCLI_STATE_PATH": str(self.nm_state_path),
            }
        )
        return subprocess.run(
            ["/bin/sh", str(HELPER_PATH), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
            cwd=Path.cwd(),
        )

    def write_nm_state(self, payload: dict[str, object]) -> None:
        data: NmState = {"connections": [], "active_connection": None}
        data.update(payload)
        connections = data.get("connections", [])
        assert isinstance(connections, list)
        for connection in connections:
            assert isinstance(connection, dict)
            if connection.get("active") is True:
                data["active_connection"] = connection.get("name")
                break
        self.nm_state_path.write_text(json.dumps(data), encoding="utf-8")

    def read_nm_state(self) -> NmState:
        payload = json.loads(self.nm_state_path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        return payload

    def active_connection(self) -> dict[str, Any] | None:
        state = self.read_nm_state()
        active_name = state.get("active_connection")
        connections = state.get("connections", [])
        assert isinstance(connections, list)
        for connection in connections:
            if isinstance(connection, dict) and connection.get("name") == active_name:
                return connection
        return None


_FAKE_NMCLI = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json
    import os
    import sys
    from pathlib import Path

    state_path = Path(os.environ["FAKE_NMCLI_STATE_PATH"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    args = sys.argv[1:]

    def save() -> None:
        state_path.write_text(json.dumps(state), encoding="utf-8")

    def get_connections():
        return state.setdefault("connections", [])

    def set_active(name):
        state["active_connection"] = name
        for connection in get_connections():
            connection["active"] = connection.get("name") == name
        save()

    if args[:4] == ["-t", "-f", "DEVICE,TYPE,STATE", "device"] and args[4:] == ["status"]:
        active_name = state.get("active_connection")
        active_mode = "disconnected"
        if active_name:
            active_mode = "connected"
        sys.stdout.write(f"wlan0:wifi:{active_mode}\\n")
        raise SystemExit(0)

    if args[:4] == ["-t", "-f", "TYPE,NAME", "connection"] and args[4] == "show":
        only_active = args[5:] == ["--active"]
        lines = []
        for connection in get_connections():
            if only_active and not connection.get("active"):
                continue
            lines.append(f"{connection.get('type')}:{connection.get('name')}")
        sys.stdout.write("\\n".join(lines))
        if lines:
            sys.stdout.write("\\n")
        raise SystemExit(0)

    if args[:3] == ["device", "wifi", "hotspot"]:
        name = args[args.index("con-name") + 1]
        ssid = args[args.index("ssid") + 1]
        password = args[args.index("password") + 1]
        connections = [c for c in get_connections() if c.get("name") != name]
        connections.append(
            {
                "name": name,
                "type": "802-11-wireless",
                "mode": "ap",
                "ssid": ssid,
                "password": password,
                "active": True,
            }
        )
        state["connections"] = connections
        set_active(name)
        raise SystemExit(0)

    if args[:3] == ["device", "wifi", "connect"]:
        ssid = args[3]
        password = ""
        if "password" in args:
            password = args[args.index("password") + 1]
        name = args[args.index("name") + 1]
        connections = [c for c in get_connections() if c.get("name") != name]
        connections.append(
            {
                "name": name,
                "type": "802-11-wireless",
                "mode": "client",
                "ssid": ssid,
                "password": password,
                "active": True,
            }
        )
        state["connections"] = connections
        set_active(name)
        raise SystemExit(0)

    if args[:2] == ["connection", "up"]:
        name = args[args.index("id") + 1]
        set_active(name)
        raise SystemExit(0)

    if args[:2] == ["connection", "down"]:
        name = args[args.index("id") + 1]
        if state.get("active_connection") == name:
            state["active_connection"] = None
        for connection in get_connections():
            if connection.get("name") == name:
                connection["active"] = False
        save()
        raise SystemExit(0)

    if args[:2] == ["connection", "delete"]:
        name = args[args.index("id") + 1]
        state["connections"] = [c for c in get_connections() if c.get("name") != name]
        if state.get("active_connection") == name:
            state["active_connection"] = None
        save()
        raise SystemExit(0)

    sys.stderr.write(f"unsupported fake nmcli call: {args!r}\\n")
    raise SystemExit(2)
    """
)
