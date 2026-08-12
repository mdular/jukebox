from __future__ import annotations

import pytest
from jukebox.core.parser import parse_spotify_uri

from cardmaker.references import InvalidSpotifyReference, SpotifyReferenceParser

SPOTIFY_ID = "2takcwOaAZWiXQijPHIx7B"


@pytest.mark.parametrize(
    "raw",
    [
        f"spotify:track:{SPOTIFY_ID}",
        f"https://open.spotify.com/track/{SPOTIFY_ID}",
        f"https://open.spotify.com/track/{SPOTIFY_ID}?si=tracking#fragment",
        f"https://open.spotify.com/intl-de/track/{SPOTIFY_ID}?si=tracking",
    ],
)
def test_parse_normalizes_track_references(raw: str) -> None:
    reference = SpotifyReferenceParser().parse(raw)

    assert reference.kind == "track"
    assert reference.spotify_id == SPOTIFY_ID
    assert reference.uri == f"spotify:track:{SPOTIFY_ID}"
    assert reference.external_url == f"https://open.spotify.com/track/{SPOTIFY_ID}"


@pytest.mark.parametrize("kind", ["track", "album", "playlist"])
def test_normalized_references_match_jukebox_parser_contract(kind: str) -> None:
    reference = SpotifyReferenceParser().parse(f"spotify:{kind}:{SPOTIFY_ID}")

    parsed = parse_spotify_uri(reference.uri)

    assert parsed.kind == kind
    assert parsed.spotify_id == SPOTIFY_ID


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        f"spotify:artist:{SPOTIFY_ID}",
        f"spotify:episode:{SPOTIFY_ID}",
        f"spotify:local:{SPOTIFY_ID}",
        "spotify:track:too-short",
        f"https://example.com/track/{SPOTIFY_ID}",
        f"http://open.spotify.com/track/{SPOTIFY_ID}",
        f"https://open.spotify.com/artist/{SPOTIFY_ID}",
        f"https://open.spotify.com/track/{SPOTIFY_ID}/extra",
        "https://spotify.link/short",
        f"https://open.spotify.com/embed/track/{SPOTIFY_ID}",
        f"https://user:password@open.spotify.com/track/{SPOTIFY_ID}",
    ],
)
def test_parse_rejects_unsupported_or_unsafe_references(raw: str) -> None:
    with pytest.raises(InvalidSpotifyReference):
        SpotifyReferenceParser().parse(raw)
