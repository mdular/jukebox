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


class _WifiHelper:
    def __init__(self, *, has_client_config: bool = True) -> None:
        self.has_client_config = has_client_config
        self.start_setup_ap_called = False

    def status(self) -> dict[str, bool]:
        return {
            "has_client_config": self.has_client_config,
            "client_connected": self.has_client_config,
            "ap_active": False,
        }

    def start_setup_ap(self) -> tuple[bool, str]:
        self.start_setup_ap_called = True
        return True, "setup ap started"
