"""Setup and auth mode state management."""

from __future__ import annotations

from typing import Protocol

from .operator_state import OperatorStateStore
from .runtime_health import DependencyStatus


class WifiHelper(Protocol):
    """Minimal Wi-Fi helper surface for setup mode."""

    def status(self) -> dict[str, bool]:
        """Return Wi-Fi state flags."""

    def start_setup_ap(self) -> tuple[bool, str]:
        """Start setup AP mode."""


class SetupModeManager:
    """Translate persisted setup flags and Wi-Fi state into readiness."""

    def __init__(self, *, operator_state: OperatorStateStore, wifi_helper: WifiHelper) -> None:
        self._operator_state = operator_state
        self._wifi_helper = wifi_helper

    def initialize(self) -> DependencyStatus:
        """Evaluate boot-time setup fallback conditions."""

        current = self._operator_state.load()
        if current.receiver_reauth_requested:
            return self._auth_required_status()
        if current.setup_requested:
            self._wifi_helper.start_setup_ap()
            return self._setup_required_status()

        wifi_status = self._wifi_helper.status()
        if not wifi_status.get("has_client_config", False):
            self._wifi_helper.start_setup_ap()
            self._operator_state.mark_setup_requested(True, wifi_mode="setup_ap")
            return self._setup_required_status()
        return self._ready_status()

    def status(self) -> DependencyStatus:
        """Return the current setup/auth readiness status."""

        current = self._operator_state.load()
        if current.receiver_reauth_requested:
            return self._auth_required_status()
        if current.setup_requested or current.last_wifi_mode == "setup_ap":
            return self._setup_required_status()

        wifi_status = self._wifi_helper.status()
        if wifi_status.get("ap_active", False):
            return self._setup_required_status()
        return self._ready_status()

    def _ready_status(self) -> DependencyStatus:
        return DependencyStatus(code="ready", ready=True, message="waiting for scan input")

    def _setup_required_status(self) -> DependencyStatus:
        return DependencyStatus(
            code="setup_required",
            ready=False,
            message="setup required",
            source="setup",
        )

    def _auth_required_status(self) -> DependencyStatus:
        return DependencyStatus(
            code="auth_required",
            ready=False,
            message="auth required",
            source="setup",
        )
