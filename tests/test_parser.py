"""Tests for strict scan payload parsing."""

import unittest

from jukebox.core.cards import JukeboxActionCard, SpotifyMediaCard
from jukebox.core.parser import (
    InvalidPayloadError,
    UnsupportedContentError,
    parse_scan_payload,
    parse_spotify_uri,
)


class ParseSpotifyUriTests(unittest.TestCase):
    def test_valid_track_uri_is_parsed(self) -> None:
        parsed = parse_spotify_uri("spotify:track:6rqhFgbbKwnb9MLmUQDhG6")

        self.assertEqual(parsed.kind, "track")
        self.assertEqual(parsed.spotify_id, "6rqhFgbbKwnb9MLmUQDhG6")

    def test_valid_album_uri_is_parsed(self) -> None:
        parsed = parse_spotify_uri("spotify:album:1ATL5GLyefJaxhQzSPVrLX")

        self.assertEqual(parsed.kind, "album")
        self.assertEqual(parsed.spotify_id, "1ATL5GLyefJaxhQzSPVrLX")

    def test_valid_playlist_uri_is_parsed(self) -> None:
        parsed = parse_spotify_uri("spotify:playlist:37i9dQZF1DXcBWIGoYBM5M")

        self.assertEqual(parsed.kind, "playlist")
        self.assertEqual(parsed.spotify_id, "37i9dQZF1DXcBWIGoYBM5M")

    def test_invalid_payload_raises_invalid_payload_error(self) -> None:
        with self.assertRaises(InvalidPayloadError):
            parse_spotify_uri("https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6")

    def test_unsupported_spotify_uri_type_raises_unsupported_content_error(self) -> None:
        with self.assertRaises(UnsupportedContentError):
            parse_spotify_uri("spotify:artist:4gzpq5DPGxSnKTe4SA8HAU")

    def test_trailing_spaces_are_not_trimmed(self) -> None:
        with self.assertRaises(InvalidPayloadError):
            parse_spotify_uri("spotify:track:6rqhFgbbKwnb9MLmUQDhG6 ")


class ParseScanPayloadTests(unittest.TestCase):
    def test_valid_jukebox_action_card_is_parsed(self) -> None:
        parsed = parse_scan_payload("jukebox:playback:stop")

        assert isinstance(parsed, JukeboxActionCard)
        self.assertEqual(parsed.group, "playback")
        self.assertEqual(parsed.action, "stop")
        self.assertEqual(parsed.action_id, "playback.stop")

    def test_unsupported_jukebox_action_is_still_parsed(self) -> None:
        parsed = parse_scan_payload("jukebox:lights:blink")

        assert isinstance(parsed, JukeboxActionCard)
        self.assertEqual(parsed.action_id, "lights.blink")

    def test_scan_payload_preserves_spotify_parsing(self) -> None:
        parsed = parse_scan_payload("spotify:album:1ATL5GLyefJaxhQzSPVrLX")

        assert isinstance(parsed, SpotifyMediaCard)
        self.assertEqual(parsed.kind, "album")
        self.assertEqual(parsed.spotify_id, "1ATL5GLyefJaxhQzSPVrLX")

    def test_invalid_jukebox_payload_raises_invalid_payload_error(self) -> None:
        with self.assertRaises(InvalidPayloadError):
            parse_scan_payload("jukebox:playback")

    def test_invalid_action_token_raises_invalid_payload_error(self) -> None:
        with self.assertRaises(InvalidPayloadError):
            parse_scan_payload("jukebox:playback:STOP")
