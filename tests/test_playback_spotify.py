"""Tests for the Spotify playback backend."""

from __future__ import annotations

import base64
import json
import unittest
from email.message import Message
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.request import Request

from jukebox.adapters.playback_spotify import ResponseLike, SpotifyPlaybackBackend
from jukebox.core.models import PlaybackRequest, SpotifyUri, SpotifyUriKind


class SpotifyPlaybackBackendTests(unittest.TestCase):
    def test_track_dispatch_uses_uri_list_payload_and_device_query(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(204, None),
            ]
        )
        backend = SpotifyPlaybackBackend(
            client_id="client-id",
            client_secret="client-secret",
            refresh_token="refresh-token",
            device_id="device-id",
            requester=requester,
        )

        result = backend.dispatch(_request("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "track"))

        self.assertTrue(result.ok)
        token_request, play_request = requester.requests
        self.assertEqual(token_request.full_url, "https://accounts.spotify.com/api/token")
        self.assertIn("Basic ", token_request.get_header("Authorization") or "")
        self.assertEqual(
            token_request.data,
            b"grant_type=refresh_token&refresh_token=refresh-token",
        )
        self.assertEqual(
            play_request.full_url,
            "https://api.spotify.com/v1/me/player/play?device_id=device-id",
        )
        self.assertEqual(play_request.get_header("Authorization"), "Bearer access-token")
        self.assertEqual(
            json.loads(cast(bytes, play_request.data).decode("utf-8")),
            {"uris": ["spotify:track:6rqhFgbbKwnb9MLmUQDhG6"]},
        )

        expected_basic = base64.b64encode(b"client-id:client-secret").decode("ascii")
        self.assertEqual(token_request.get_header("Authorization"), f"Basic {expected_basic}")

    def test_context_dispatch_uses_context_uri_payload(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(204, None),
            ]
        )
        backend = SpotifyPlaybackBackend(
            client_id="client-id",
            client_secret="client-secret",
            refresh_token="refresh-token",
            requester=requester,
        )

        result = backend.dispatch(_request("spotify:album:1ATL5GLyefJaxhQzSPVrLX", "album"))

        self.assertTrue(result.ok)
        play_request = requester.requests[1]
        self.assertEqual(
            json.loads(cast(bytes, play_request.data).decode("utf-8")),
            {"context_uri": "spotify:album:1ATL5GLyefJaxhQzSPVrLX"},
        )
        self.assertEqual(play_request.full_url, "https://api.spotify.com/v1/me/player/play")

    def test_http_404_maps_to_no_active_device(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                HTTPError(
                    url="https://api.spotify.com/v1/me/player/play",
                    code=404,
                    msg="Not Found",
                    hdrs=Message(),
                    fp=None,
                ),
            ]
        )
        backend = SpotifyPlaybackBackend(
            client_id="client-id",
            client_secret="client-secret",
            refresh_token="refresh-token",
            requester=requester,
        )

        result = backend.dispatch(_request("spotify:playlist:37i9dQZF1DXcBWIGoYBM5M", "playlist"))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "spotify_no_active_device")

    def test_transport_errors_are_mapped(self) -> None:
        requester = _SequenceRequester([URLError("network down")])
        backend = SpotifyPlaybackBackend(
            client_id="client-id",
            client_secret="client-secret",
            refresh_token="refresh-token",
            requester=requester,
        )

        result = backend.dispatch(_request("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "track"))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "spotify_transport_error")


def _request(raw: str, kind: SpotifyUriKind) -> PlaybackRequest:
    return PlaybackRequest(uri=SpotifyUri(raw=raw, kind=kind, spotify_id=raw.rsplit(":", 1)[1]))


class _SequenceRequester:
    def __init__(self, responses: list[ResponseLike | Exception]) -> None:
        self._responses = responses
        self.requests: list[Request] = []

    def __call__(self, request: Request, timeout_seconds: float) -> ResponseLike:
        del timeout_seconds
        self.requests.append(request)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _FakeResponse:
    def __init__(self, status: int, payload: dict[str, object] | None) -> None:
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        if self._payload is None:
            return b""
        return json.dumps(self._payload).encode("utf-8")
