"""Tests for setup/auth mode management."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jukebox.operator_state import OperatorStateStore
from jukebox.setup_mode import SetupModeManager


class SetupModeManagerTests(unittest.TestCase):
    def test_setup_requested_surfaces_setup_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = OperatorStateStore(Path(temp_dir) / "state.json")
            store.mark_setup_requested(True, wifi_mode="setup_ap")
            manager = SetupModeManager(operator_state=store, wifi_helper=_WifiHelper())

            status = manager.status()

            self.assertFalse(status.ready)
            self.assertEqual(status.code, "setup_required")

    def test_missing_client_config_enters_setup_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = OperatorStateStore(Path(temp_dir) / "state.json")
            helper = _WifiHelper(has_client_config=False)
            manager = SetupModeManager(operator_state=store, wifi_helper=helper)

            status = manager.initialize()

            self.assertEqual(status.code, "setup_required")
            self.assertTrue(helper.start_setup_ap_called)

    def test_receiver_reauth_surfaces_auth_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = OperatorStateStore(Path(temp_dir) / "state.json")
            store.mark_receiver_reauth_requested(True)
            manager = SetupModeManager(operator_state=store, wifi_helper=_WifiHelper())

            status = manager.status()

            self.assertFalse(status.ready)
            self.assertEqual(status.code, "auth_required")

    def test_unreachable_configured_network_enters_setup_after_grace_period(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = OperatorStateStore(Path(temp_dir) / "state.json")
            helper = _WifiHelper(
                status_sequence=[
                    {"has_client_config": True, "client_connected": False, "ap_active": False},
                    {"has_client_config": True, "client_connected": False, "ap_active": False},
                    {"has_client_config": True, "client_connected": False, "ap_active": False},
                ]
            )
            manager = SetupModeManager(
                operator_state=store,
                wifi_helper=helper,
                fallback_grace_seconds=5.0,
                clock=_FakeClock([0.0, 0.0, 3.0, 6.0]),
                sleeper=lambda seconds: None,
            )

            status = manager.initialize()

            self.assertEqual(status.code, "setup_required")
            self.assertTrue(helper.start_setup_ap_called)
            self.assertEqual(store.load().last_wifi_mode, "setup_ap")

    def test_recovered_connectivity_within_grace_period_stays_in_client_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = OperatorStateStore(Path(temp_dir) / "state.json")
            helper = _WifiHelper(
                status_sequence=[
                    {"has_client_config": True, "client_connected": False, "ap_active": False},
                    {"has_client_config": True, "client_connected": True, "ap_active": False},
                ]
            )
            manager = SetupModeManager(
                operator_state=store,
                wifi_helper=helper,
                fallback_grace_seconds=5.0,
                clock=_FakeClock([0.0, 0.0, 2.0]),
                sleeper=lambda seconds: None,
            )

            status = manager.initialize()

            self.assertEqual(status.code, "ready")
            self.assertFalse(helper.start_setup_ap_called)
            self.assertEqual(store.load().last_wifi_mode, "client")


class _WifiHelper:
    def __init__(
        self,
        *,
        has_client_config: bool = True,
        status_sequence: list[dict[str, bool]] | None = None,
    ) -> None:
        self.has_client_config = has_client_config
        self.start_setup_ap_called = False
        self._status_sequence = status_sequence or []

    def status(self) -> dict[str, bool]:
        if self._status_sequence:
            return self._status_sequence.pop(0)
        return {
            "has_client_config": self.has_client_config,
            "client_connected": self.has_client_config,
            "ap_active": False,
        }

    def start_setup_ap(self) -> tuple[bool, str]:
        self.start_setup_ap_called = True
        return True, "setup ap started"


class _FakeClock:
    def __init__(self, values: list[float]) -> None:
        self._values = values
        self._last = values[-1]

    def __call__(self) -> float:
        if not self._values:
            return self._last
        self._last = self._values.pop(0)
        return self._last
