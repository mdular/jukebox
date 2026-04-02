"""Typed card models and action identifiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

SpotifyUriKind = Literal["track", "album", "playlist"]
PlaybackMode = Literal["replace", "queue_tracks"]


@dataclass(frozen=True)
class SpotifyMediaCard:
    """Validated Spotify media card."""

    raw: str
    kind: SpotifyUriKind
    spotify_id: str


@dataclass(frozen=True)
class JukeboxActionCard:
    """Validated jukebox action card."""

    raw: str
    group: str
    action: str
    action_id: str


ParsedCard = SpotifyMediaCard | JukeboxActionCard

SUPPORTED_ACTION_IDS: Final[frozenset[str]] = frozenset(
    {
        "playback.stop",
        "playback.next",
        "mode.replace",
        "mode.queue",
        "volume.low",
        "volume.medium",
        "volume.high",
        "setup.wifi-reset",
        "setup.receiver-reauth",
        "system.shutdown",
    }
)

DEFAULT_ENABLED_ACTION_IDS: Final[frozenset[str]] = SUPPORTED_ACTION_IDS
