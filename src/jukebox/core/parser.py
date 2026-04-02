"""Strict Spotify URI parsing."""

from __future__ import annotations

import re
from typing import Final, cast

from .cards import JukeboxActionCard, ParsedCard, SpotifyMediaCard, SpotifyUriKind

_SPOTIFY_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9]{22}$")
_SUPPORTED_KINDS: Final[frozenset[str]] = frozenset({"track", "album", "playlist"})
_ACTION_TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9-]*$")


class ParseError(ValueError):
    """Base error for scan payload parsing failures."""

    reason_code: str

    def __init__(self, message: str, *, reason_code: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class InvalidPayloadError(ParseError):
    """Raised for malformed or unsupported payload shapes."""

    def __init__(self, message: str) -> None:
        super().__init__(message, reason_code="invalid_uri")


class UnsupportedContentError(ParseError):
    """Raised for well-formed Spotify URIs outside the supported content set."""

    def __init__(self, message: str) -> None:
        super().__init__(message, reason_code="unsupported_content")


def parse_spotify_uri(raw: str) -> SpotifyMediaCard:
    """Parse a strict Spotify URI into a strongly typed model."""

    parts = raw.split(":")
    if len(parts) != 3:
        raise InvalidPayloadError("Expected spotify:(track|album|playlist):<id>.")

    provider, kind, spotify_id = parts
    if provider != "spotify":
        raise InvalidPayloadError("Expected spotify:(track|album|playlist):<id>.")
    if not kind:
        raise InvalidPayloadError("Expected spotify:(track|album|playlist):<id>.")
    if not _SPOTIFY_ID_PATTERN.fullmatch(spotify_id):
        raise InvalidPayloadError("Expected spotify:(track|album|playlist):<id>.")
    if kind not in _SUPPORTED_KINDS:
        raise UnsupportedContentError(f"Unsupported Spotify URI type: {kind}.")

    return SpotifyMediaCard(raw=raw, kind=cast(SpotifyUriKind, kind), spotify_id=spotify_id)


def parse_scan_payload(raw: str) -> ParsedCard:
    """Parse a Spotify media card or jukebox action card."""

    parts = raw.split(":")
    if len(parts) != 3:
        raise InvalidPayloadError(
            "Expected spotify:(track|album|playlist):<id> or jukebox:<group>:<action>."
        )

    provider, middle, tail = parts
    if provider == "spotify":
        return parse_spotify_uri(raw)
    if provider != "jukebox":
        raise InvalidPayloadError(
            "Expected spotify:(track|album|playlist):<id> or jukebox:<group>:<action>."
        )
    if not _ACTION_TOKEN_PATTERN.fullmatch(middle):
        raise InvalidPayloadError("Expected jukebox:<group>:<action>.")
    if not _ACTION_TOKEN_PATTERN.fullmatch(tail):
        raise InvalidPayloadError("Expected jukebox:<group>:<action>.")
    return JukeboxActionCard(
        raw=raw,
        group=middle,
        action=tail,
        action_id=f"{middle}.{tail}",
    )
