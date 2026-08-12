"""Strict parsing and canonicalization of supported Spotify references."""

from __future__ import annotations

import re
from typing import Final, cast
from urllib.parse import urlsplit

from .models import SpotifyKind, SpotifyReference

_URI_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^spotify:(track|album|playlist):([A-Za-z0-9]{22})$"
)
_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9]{22}$")
_LOCALE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^intl-[A-Za-z]{2}$")
_SUPPORTED_KINDS: Final[frozenset[str]] = frozenset({"track", "album", "playlist"})


class InvalidSpotifyReference(ValueError):
    """Raised when a pasted value is not a supported Spotify URI or share URL."""

    code = "invalid_reference"


class SpotifyReferenceParser:
    """Normalize supported Spotify URIs and open.spotify.com share URLs."""

    def parse(self, raw: str) -> SpotifyReference:
        value = raw.strip()
        uri_match = _URI_PATTERN.fullmatch(value)
        if uri_match is not None:
            kind, spotify_id = uri_match.groups()
            return SpotifyReference(cast(SpotifyKind, kind), spotify_id)

        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "open.spotify.com"
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise InvalidSpotifyReference(
                "Enter a supported Spotify track, album, or playlist URL or URI."
            )

        parts = [part for part in parsed.path.split("/") if part]
        if parts and _LOCALE_PATTERN.fullmatch(parts[0]):
            parts = parts[1:]
        if len(parts) != 2:
            raise InvalidSpotifyReference(
                "Spotify share URLs must identify one track, album, or playlist."
            )

        kind, spotify_id = parts
        if kind not in _SUPPORTED_KINDS or not _ID_PATTERN.fullmatch(spotify_id):
            raise InvalidSpotifyReference(
                "Enter a supported Spotify track, album, or playlist URL or URI."
            )
        return SpotifyReference(cast(SpotifyKind, kind), spotify_id)
