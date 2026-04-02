"""Setup and auth mode state management."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from .operator_state import OperatorStateStore
from .runtime_health import DependencyStatus

Clock = Callable[[], float]
Sleeper = Callable[[float], None]


class WifiHelper(Protocol):
    """Minimal Wi-Fi helper surface for setup mode."""

    def status(self) -> dict[str, bool]:
        """Return Wi-Fi state flags."""

    def start_setup_ap(self) -> tuple[bool, str]:
        """Start setup AP mode."""


class SetupModeManager:
    """Translate persisted setup flags and Wi-Fi state into readiness."""

    def __init__(
        self,
        *,
        operator_state: OperatorStateStore,
        wifi_helper: WifiHelper,
        fallback_grace_seconds: float = 120.0,
        poll_interval_seconds: float = 1.0,
        clock: Clock | None = None,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._operator_state = operator_state
        self._wifi_helper = wifi_helper
        self._fallback_grace_seconds = fallback_grace_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._clock = time.monotonic if clock is None else clock
        self._sleeper = time.sleep if sleeper is None else sleeper

    def initialize(self) -> DependencyStatus:
        """Evaluate boot-time setup fallback conditions."""

        current = self._operator_state.load()
        if current.receiver_reauth_requested:
            return self._auth_required_status()
        if current.setup_requested:
            return self._enter_setup_mode()

        wifi_status = self._wifi_helper.status()
        if not wifi_status.get("has_client_config", False):
            return self._enter_setup_mode()
        if wifi_status.get("client_connected", False):
            self._operator_state.mark_setup_requested(False, wifi_mode="client")
            return self._ready_status()

        deadline = self._clock() + self._fallback_grace_seconds
        while self._clock() < deadline:
            self._sleeper(self._poll_interval_seconds)
            wifi_status = self._wifi_helper.status()
            if wifi_status.get("client_connected", False):
                self._operator_state.mark_setup_requested(False, wifi_mode="client")
                return self._ready_status()
            if wifi_status.get("ap_active", False):
                self._operator_state.mark_setup_requested(True, wifi_mode="setup_ap")
                return self._setup_required_status()
        return self._enter_setup_mode()

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

    def _enter_setup_mode(self) -> DependencyStatus:
        ok, message = self._wifi_helper.start_setup_ap()
        if not ok:
            raise RuntimeError(message)
        self._operator_state.mark_setup_requested(True, wifi_mode="setup_ap")
        return self._setup_required_status()
