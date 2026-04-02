"""Routing for typed jukebox action cards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from ..core.cards import JukeboxActionCard
from ..core.models import ActionResult, PlaybackBackend, PlaybackResult
from ..operator_state import OperatorStateStore


class SystemHelpers(Protocol):
    """System-side helper adapter contract."""

    def reset_wifi(self) -> tuple[bool, str]:
        """Clear client Wi-Fi config and re-enter setup mode."""

    def request_shutdown(self, *, reason: str) -> tuple[bool, str]:
        """Request graceful OS shutdown."""


@dataclass
class ActionRouter:
    """Map typed action cards onto runtime behavior."""

    playback_backend: PlaybackBackend
    operator_state: OperatorStateStore
    system_helpers: SystemHelpers
    volume_presets: Mapping[str, int]

    def execute(self, card: JukeboxActionCard) -> ActionResult:
        action_id = card.action_id
        if action_id == "playback.stop":
            return self._from_playback_result(
                self.playback_backend.stop(), action_id=action_id, action_scope="child"
            )
        if action_id == "playback.next":
            return self._from_playback_result(
                self.playback_backend.skip_next(), action_id=action_id, action_scope="child"
            )
        if action_id == "mode.replace":
            self.operator_state.set_playback_mode("replace")
            return ActionResult(
                ok=True,
                action_id=action_id,
                action_scope="child",
                message="playback mode set to replace",
                playback_mode="replace",
            )
        if action_id == "mode.queue":
            self.operator_state.set_playback_mode("queue_tracks")
            return ActionResult(
                ok=True,
                action_id=action_id,
                action_scope="child",
                message="playback mode set to queue_tracks",
                playback_mode="queue_tracks",
            )
        if action_id in {"volume.low", "volume.medium", "volume.high"}:
            preset_name = card.action
            percent = self.volume_presets.get(preset_name)
            if percent is None:
                return ActionResult(
                    ok=False,
                    action_id=action_id,
                    action_scope="child",
                    reason_code="unsupported_action",
                    message="volume preset unavailable",
                )
            return self._from_playback_result(
                self.playback_backend.set_volume_percent(percent),
                action_id=action_id,
                action_scope="child",
            )
        if action_id == "setup.wifi-reset":
            ok, message = self.system_helpers.reset_wifi()
            if not ok:
                return ActionResult(
                    ok=False,
                    action_id=action_id,
                    action_scope="operator",
                    reason_code="setup_action_failed",
                    message=message,
                )
            self.operator_state.mark_setup_requested(True, wifi_mode="setup_ap")
            return ActionResult(
                ok=True,
                action_id=action_id,
                action_scope="operator",
                message=message,
                setup_mode="setup_ap",
            )
        if action_id == "setup.receiver-reauth":
            self.operator_state.mark_receiver_reauth_requested(True)
            return ActionResult(
                ok=True,
                action_id=action_id,
                action_scope="operator",
                message="receiver re-auth required",
                setup_mode="auth_required",
            )
        if action_id == "system.shutdown":
            ok, message = self.system_helpers.request_shutdown(reason="action")
            if not ok:
                return ActionResult(
                    ok=False,
                    action_id=action_id,
                    action_scope="operator",
                    reason_code="system_action_failed",
                    message=message,
                )
            return ActionResult(
                ok=True,
                action_id=action_id,
                action_scope="operator",
                message=message,
            )
        return ActionResult(
            ok=False,
            action_id=action_id,
            action_scope="operator" if card.group in {"setup", "system"} else "child",
            reason_code="unsupported_action",
            message=f"unsupported action: {action_id}",
        )

    def _from_playback_result(
        self,
        result: PlaybackResult,
        *,
        action_id: str,
        action_scope: str,
    ) -> ActionResult:
        return ActionResult(
            ok=result.ok,
            action_id=action_id,
            action_scope="operator" if action_scope == "operator" else "child",
            reason_code=result.reason_code,
            message=result.message or "action completed" if result.ok else "action failed",
        )
