"""Core data models for the Jukebox controller."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, TypeAlias

from .cards import PlaybackMode, SpotifyMediaCard

SpotifyUri = SpotifyMediaCard
SpotifyUriKind: TypeAlias = Literal["track", "album", "playlist"]


@dataclass(frozen=True)
class PlaybackRequest:
    """A request to dispatch playback for a parsed URI."""

    uri: SpotifyUri


@dataclass(frozen=True)
class PlaybackResult:
    """The backend result for a playback dispatch attempt."""

    ok: bool
    backend: str
    reason_code: str | None = None
    message: str | None = None
    device_name: str | None = None


@dataclass(frozen=True)
class ActionResult:
    """The result of executing a jukebox action card."""

    ok: bool
    action_id: str
    message: str
    reason_code: str | None = None
    action_scope: Literal["child", "operator"] | None = None
    playback_mode: PlaybackMode | None = None
    setup_mode: Literal["client", "setup_ap", "auth_required"] | None = None


@dataclass(frozen=True)
class ControllerEvent:
    """An observable controller outcome."""

    code: str
    message: str
    payload: str | None = None
    card_kind: Literal["media", "action"] | None = None
    uri_kind: str | None = None
    action_name: str | None = None
    action_scope: Literal["child", "operator"] | None = None
    backend: str | None = None
    reason_code: str | None = None
    device_name: str | None = None
    source: str | None = None
    playback_mode: PlaybackMode | None = None
    setup_mode: Literal["client", "setup_ap", "auth_required"] | None = None


class PlaybackBackend(Protocol):
    """Playback adapter contract."""

    def probe(self) -> PlaybackResult:
        """Probe backend readiness for startup checks."""

    def dispatch(self, request: PlaybackRequest) -> PlaybackResult:
        """Dispatch the requested playback action."""

    def enqueue(self, request: PlaybackRequest) -> PlaybackResult:
        """Queue the requested track for playback."""

    def stop(self) -> PlaybackResult:
        """Stop or pause the current playback."""

    def skip_next(self) -> PlaybackResult:
        """Advance to the next playback item."""

    def set_volume_percent(self, percent: int) -> PlaybackResult:
        """Apply a software volume percentage."""

    def player_active(self) -> bool | None:
        """Return whether playback is currently active on the target device."""


class EventSink(Protocol):
    """Observer contract for controller events."""

    def handle(self, event: ControllerEvent) -> None:
        """Handle one controller event."""
