"""Core data models for the Jukebox controller."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

SpotifyUriKind = Literal["track", "album", "playlist"]


@dataclass(frozen=True)
class SpotifyUri:
    """Validated Spotify URI information."""

    raw: str
    kind: SpotifyUriKind
    spotify_id: str


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


@dataclass(frozen=True)
class ControllerEvent:
    """An observable controller outcome."""

    code: str
    message: str
    payload: str | None = None
    uri_kind: str | None = None
    backend: str | None = None
    reason_code: str | None = None


class PlaybackBackend(Protocol):
    """Playback adapter contract."""

    def dispatch(self, request: PlaybackRequest) -> PlaybackResult:
        """Dispatch the requested playback action."""


class EventSink(Protocol):
    """Observer contract for controller events."""

    def handle(self, event: ControllerEvent) -> None:
        """Handle one controller event."""
