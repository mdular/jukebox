"""Persisted non-secret operator state."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .core.cards import DEFAULT_ENABLED_ACTION_IDS, PlaybackMode

WifiMode = Literal["client", "setup_ap"]
_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class OperatorState:
    """Persisted operator preferences and mode flags."""

    playback_mode: PlaybackMode = "replace"
    setup_requested: bool = False
    receiver_reauth_requested: bool = False
    last_wifi_mode: WifiMode | None = None
    enabled_actions: frozenset[str] = DEFAULT_ENABLED_ACTION_IDS
    schema_version: int = _SCHEMA_VERSION


class OperatorStateStore:
    """Read and write operator state on disk."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> OperatorState:
        if not self._path.exists():
            state = OperatorState()
            self.save(state)
            return state

        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state = OperatorState()
            self.save(state)
            return state

        state = self._decode(payload)
        self.save(state)
        return state

    def save(self, state: OperatorState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(state)
        payload["enabled_actions"] = sorted(state.enabled_actions)
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def set_playback_mode(self, playback_mode: PlaybackMode) -> OperatorState:
        current = self.load()
        updated = OperatorState(
            playback_mode=playback_mode,
            setup_requested=current.setup_requested,
            receiver_reauth_requested=current.receiver_reauth_requested,
            last_wifi_mode=current.last_wifi_mode,
            enabled_actions=current.enabled_actions,
        )
        self.save(updated)
        return updated

    def mark_setup_requested(self, requested: bool, *, wifi_mode: WifiMode | None) -> OperatorState:
        current = self.load()
        updated = OperatorState(
            playback_mode=current.playback_mode,
            setup_requested=requested,
            receiver_reauth_requested=current.receiver_reauth_requested,
            last_wifi_mode=wifi_mode,
            enabled_actions=current.enabled_actions,
        )
        self.save(updated)
        return updated

    def mark_receiver_reauth_requested(self, requested: bool) -> OperatorState:
        current = self.load()
        updated = OperatorState(
            playback_mode=current.playback_mode,
            setup_requested=current.setup_requested,
            receiver_reauth_requested=requested,
            last_wifi_mode=current.last_wifi_mode,
            enabled_actions=current.enabled_actions,
        )
        self.save(updated)
        return updated

    def _decode(self, payload: object) -> OperatorState:
        if not isinstance(payload, dict):
            return OperatorState()

        raw_playback_mode = payload.get("playback_mode")
        if raw_playback_mode in {"replace", "queue_tracks"}:
            playback_mode = raw_playback_mode
        else:
            playback_mode = "replace"

        raw_last_wifi_mode = payload.get("last_wifi_mode")
        last_wifi_mode: WifiMode | None
        if raw_last_wifi_mode in {"client", "setup_ap"}:
            last_wifi_mode = raw_last_wifi_mode
        else:
            last_wifi_mode = None

        raw_enabled_actions = payload.get("enabled_actions")
        enabled_actions: frozenset[str]
        if isinstance(raw_enabled_actions, list):
            enabled_actions = frozenset(
                item for item in raw_enabled_actions if isinstance(item, str)
            ) or DEFAULT_ENABLED_ACTION_IDS
        else:
            enabled_actions = DEFAULT_ENABLED_ACTION_IDS

        return OperatorState(
            playback_mode=playback_mode,
            setup_requested=bool(payload.get("setup_requested", False)),
            receiver_reauth_requested=bool(payload.get("receiver_reauth_requested", False)),
            last_wifi_mode=last_wifi_mode,
            enabled_actions=enabled_actions,
            schema_version=_SCHEMA_VERSION,
        )
