"""Domain values shared across Card Maker use cases and adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from PIL.Image import Image

SpotifyKind = Literal["track", "album", "playlist"]

_SPOTIFY_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9]{22}$")
_SUPPORTED_KINDS: Final[frozenset[str]] = frozenset({"track", "album", "playlist"})


@dataclass(frozen=True, slots=True)
class SpotifyReference:
    """Canonical reference to one supported Spotify catalog entity."""

    kind: SpotifyKind
    spotify_id: str

    def __post_init__(self) -> None:
        if self.kind not in _SUPPORTED_KINDS:
            raise ValueError(f"Unsupported Spotify kind: {self.kind}")
        if not _SPOTIFY_ID_PATTERN.fullmatch(self.spotify_id):
            raise ValueError("Spotify IDs must contain exactly 22 base-62 characters.")

    @property
    def uri(self) -> str:
        return f"spotify:{self.kind}:{self.spotify_id}"

    @property
    def external_url(self) -> str:
        return f"https://open.spotify.com/{self.kind}/{self.spotify_id}"


@dataclass(frozen=True, slots=True)
class ArtworkReference:
    """Spotify-provided artwork provenance without downloaded bytes."""

    url: str
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True, slots=True)
class CatalogItem:
    """Catalog metadata used above the Spotify adapter."""

    reference: SpotifyReference
    primary_label: str
    secondary_label: str | None
    artwork: ArtworkReference | None
    external_url: str


@dataclass(frozen=True, slots=True)
class CardDraft:
    """Resolved catalog metadata plus in-memory Spotify artwork."""

    item: CatalogItem
    artwork: Image
    cover_source: Literal["spotify"] = "spotify"


@dataclass(frozen=True, slots=True)
class RenderedCard:
    """One verified PNG returned directly to the browser."""

    png_bytes: bytes
    normalized_uri: str
    filename: str
    width: int
    height: int
