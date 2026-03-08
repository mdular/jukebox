"""Tests for strict Spotify URI parsing."""

import unittest

from jukebox.core.parser import InvalidPayloadError, UnsupportedContentError, parse_spotify_uri


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
