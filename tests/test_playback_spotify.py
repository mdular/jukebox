"""Tests for the Spotify playback backend."""

from __future__ import annotations

import base64
import json
import unittest
from email.message import Message
from typing import cast
from urllib.error import HTTPError
from urllib.request import Request

from jukebox.adapters.playback_spotify import ResponseLike, SpotifyPlaybackBackend
from jukebox.core.cards import SpotifyUriKind
from jukebox.core.models import PlaybackRequest, SpotifyUri


class SpotifyPlaybackBackendTests(unittest.TestCase):
    def test_status_is_passive_before_probe(self) -> None:
        requester = _SequenceRequester([])
        backend = _backend(requester=requester)

        status = backend.status()

        self.assertFalse(status.ready)
        self.assertEqual(status.code, "network_unavailable")
        self.assertEqual(status.message, "Spotify status not yet determined.")
        self.assertEqual(requester.requests, [])

    def test_probe_caches_ready_status(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.probe()
        status = backend.status()

        self.assertTrue(result.ok)
        self.assertTrue(status.ready)
        self.assertEqual(status.code, "ready")
        self.assertEqual(status.device_name, "jukebox")
        self.assertEqual(
            [request.full_url for request in requester.requests],
            [
                "https://accounts.spotify.com/api/token",
                "https://api.spotify.com/v1/me/player/devices",
            ],
        )

        backend.status()
        self.assertEqual(len(requester.requests), 2)

    def test_probe_caches_controller_auth_failure(self) -> None:
        requester = _SequenceRequester([_http_error("https://accounts.spotify.com/api/token", 401)])
        backend = _backend(requester=requester)

        result = backend.probe()
        status = backend.status()

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "spotify_api_auth_error")
        self.assertFalse(status.ready)
        self.assertEqual(status.code, "controller_auth_unavailable")
        self.assertEqual(status.reason_code, "spotify_api_auth_error")

    def test_probe_retries_target_lookup_until_device_appears(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(200, {"devices": []}),
                _FakeResponse(200, {"devices": []}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
            ]
        )
        backend = _backend(requester=requester, device_probe_retry_count=5)

        result = backend.probe()
        status = backend.status()

        self.assertTrue(result.ok)
        self.assertTrue(status.ready)
        self.assertEqual(status.device_name, "jukebox")
        device_requests = [
            request
            for request in requester.requests
            if request.full_url == "https://api.spotify.com/v1/me/player/devices"
        ]
        self.assertEqual(len(device_requests), 3)

    def test_probe_caches_receiver_unavailable_after_retry_window(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(200, {"devices": []}),
                _FakeResponse(200, {"devices": []}),
                _FakeResponse(200, {"devices": []}),
            ]
        )
        backend = _backend(requester=requester, device_probe_retry_count=2)

        result = backend.probe()
        status = backend.status()

        self.assertTrue(result.ok)
        self.assertFalse(status.ready)
        self.assertEqual(status.code, "receiver_unavailable")
        self.assertEqual(status.reason_code, "device_not_listed")

    def test_probe_caches_rate_limit_message_with_retry_after(self) -> None:
        requester = _SequenceRequester(
            [_http_error("https://accounts.spotify.com/api/token", 429, retry_after=30)]
        )
        backend = _backend(requester=requester)

        result = backend.probe()
        status = backend.status()

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "spotify_rate_limited")
        self.assertFalse(status.ready)
        self.assertEqual(status.reason_code, "spotify_rate_limited")
        self.assertIn("retry in 30s", status.message)

    def test_dispatch_starts_track_directly_with_single_uri_payload(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "device-id", "name": "jukebox"},
                        "is_playing": True,
                        "item": {"uri": "spotify:track:6rqhFgbbKwnb9MLmUQDhG6"},
                    },
                ),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.dispatch(_request("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "track"))

        self.assertTrue(result.ok)
        expected_basic = base64.b64encode(b"client-id:client-secret").decode("ascii")
        self.assertEqual(
            requester.requests[0].get_header("Authorization"),
            f"Basic {expected_basic}",
        )
        self.assertEqual(
            [(request.full_url, request.get_method()) for request in requester.requests],
            [
                ("https://accounts.spotify.com/api/token", "POST"),
                ("https://api.spotify.com/v1/me/player/devices", "GET"),
                ("https://api.spotify.com/v1/me/player/play?device_id=device-id", "PUT"),
                ("https://api.spotify.com/v1/me/player", "GET"),
            ],
        )
        self.assertEqual(
            json.loads(cast(bytes, requester.requests[2].data).decode("utf-8")),
            {"uris": ["spotify:track:6rqhFgbbKwnb9MLmUQDhG6"]},
        )
        self.assertNotIn(
            "https://api.spotify.com/v1/tracks/6rqhFgbbKwnb9MLmUQDhG6",
            [request.full_url for request in requester.requests],
        )

    def test_dispatch_uses_context_uri_payload_for_albums(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "device-id", "name": "jukebox"},
                        "is_playing": True,
                        "context": {"uri": "spotify:album:1ATL5GLyefJaxhQzSPVrLX"},
                    },
                ),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.dispatch(_request("spotify:album:1ATL5GLyefJaxhQzSPVrLX", "album"))

        self.assertTrue(result.ok)
        self.assertEqual(
            json.loads(cast(bytes, requester.requests[2].data).decode("utf-8")),
            {"context_uri": "spotify:album:1ATL5GLyefJaxhQzSPVrLX"},
        )

    def test_dispatch_falls_back_to_transfer_when_direct_play_fails(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _http_error("https://api.spotify.com/v1/me/player/play", 404),
                _FakeResponse(204, None),
                _FakeResponse(204, None),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "device-id", "name": "jukebox"},
                        "is_playing": True,
                        "item": {"uri": "spotify:track:6rqhFgbbKwnb9MLmUQDhG6"},
                    },
                ),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.dispatch(_request("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "track"))

        self.assertTrue(result.ok)
        self.assertEqual(
            [(request.full_url, request.get_method()) for request in requester.requests],
            [
                ("https://accounts.spotify.com/api/token", "POST"),
                ("https://api.spotify.com/v1/me/player/devices", "GET"),
                ("https://api.spotify.com/v1/me/player/play?device_id=device-id", "PUT"),
                ("https://api.spotify.com/v1/me/player", "PUT"),
                ("https://api.spotify.com/v1/me/player/play?device_id=device-id", "PUT"),
                ("https://api.spotify.com/v1/me/player", "GET"),
            ],
        )
        self.assertEqual(
            json.loads(cast(bytes, requester.requests[3].data).decode("utf-8")),
            {"device_ids": ["device-id"], "play": False},
        )

    def test_dispatch_does_not_transfer_after_direct_play_is_rate_limited(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox"}]},
                ),
                _http_error(
                    "https://api.spotify.com/v1/me/player/play?device_id=device-id",
                    429,
                    retry_after=30,
                ),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.dispatch(_request("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "track"))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "spotify_rate_limited")
        assert result.message is not None
        self.assertIn("retry in 30s", result.message)
        self.assertEqual(
            [(request.full_url, request.get_method()) for request in requester.requests],
            [
                ("https://accounts.spotify.com/api/token", "POST"),
                ("https://api.spotify.com/v1/me/player/devices", "GET"),
                ("https://api.spotify.com/v1/me/player/play?device_id=device-id", "PUT"),
            ],
        )

    def test_dispatch_retries_once_when_target_is_not_listed_initially(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(200, {"devices": []}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "device-id", "name": "jukebox"},
                        "is_playing": True,
                        "item": {"uri": "spotify:track:6rqhFgbbKwnb9MLmUQDhG6"},
                    },
                ),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.dispatch(_request("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "track"))

        self.assertTrue(result.ok)
        device_requests = [
            request
            for request in requester.requests
            if request.full_url == "https://api.spotify.com/v1/me/player/devices"
        ]
        self.assertEqual(len(device_requests), 2)

    def test_token_is_cached_until_expiry(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "token-1", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
            ]
        )
        backend = _backend(requester=requester, clock=_FakeClock([0.0, 100.0]))

        first = backend.probe()
        second = backend.probe()

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        token_requests = [
            request
            for request in requester.requests
            if request.full_url == "https://accounts.spotify.com/api/token"
        ]
        self.assertEqual(len(token_requests), 1)

    def test_token_refreshes_after_expiry(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "token-1", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(200, {"access_token": "token-2", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
            ]
        )
        backend = _backend(requester=requester, clock=_FakeClock([0.0, 4000.0, 4000.0]))

        first = backend.probe()
        second = backend.probe()

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        token_requests = [
            request
            for request in requester.requests
            if request.full_url == "https://accounts.spotify.com/api/token"
        ]
        self.assertEqual(len(token_requests), 2)

    def test_dispatch_updates_passive_status_and_player_active_cache(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "device-id", "name": "jukebox"},
                        "is_playing": True,
                        "item": {"uri": "spotify:track:6rqhFgbbKwnb9MLmUQDhG6"},
                    },
                ),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.dispatch(_request("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "track"))
        request_count = len(requester.requests)

        self.assertTrue(result.ok)
        self.assertTrue(backend.status().ready)
        self.assertEqual(backend.status().device_name, "jukebox")
        self.assertTrue(backend.player_active())
        self.assertEqual(len(requester.requests), request_count)

    def test_stop_updates_passive_player_active_cache(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.stop()
        request_count = len(requester.requests)

        self.assertTrue(result.ok)
        self.assertFalse(backend.player_active())
        self.assertEqual(len(requester.requests), request_count)

    def test_current_player_active_is_live_scan_check(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "device-id", "name": "jukebox"},
                        "is_playing": True,
                    },
                ),
            ]
        )
        backend = _backend(requester=requester)

        current = backend.current_player_active()

        self.assertTrue(current)
        self.assertTrue(backend.player_active())
        self.assertEqual(
            [(request.full_url, request.get_method()) for request in requester.requests],
            [
                ("https://accounts.spotify.com/api/token", "POST"),
                ("https://api.spotify.com/v1/me/player", "GET"),
            ],
        )

    def test_current_player_active_returns_false_for_other_active_device(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "desktop-id", "name": "desktop"},
                        "is_playing": True,
                    },
                ),
            ]
        )
        backend = _backend(requester=requester)

        current = backend.current_player_active()

        self.assertFalse(current)
        self.assertFalse(backend.player_active())

    def test_current_player_active_caches_rate_limit_status(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _http_error("https://api.spotify.com/v1/me/player", 429, retry_after=15),
            ]
        )
        backend = _backend(requester=requester)

        current = backend.current_player_active()
        status = backend.status()

        self.assertIsNone(current)
        self.assertIsNone(backend.player_active())
        self.assertFalse(status.ready)
        self.assertEqual(status.reason_code, "spotify_rate_limited")
        self.assertIn("retry in 15s", status.message)

    def test_enqueue_calls_queue_endpoint(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token", "expires_in": 3600}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.enqueue(_request("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "track"))

        self.assertTrue(result.ok)
        self.assertEqual(
            requester.requests[2].full_url,
            "https://api.spotify.com/v1/me/player/queue?uri=spotify%3Atrack%3A6rqhFgbbKwnb9MLmUQDhG6&device_id=device-id",
        )


def _backend(
    *,
    requester: _SequenceRequester,
    confirmation_timeout_seconds: float = 5.0,
    confirmation_poll_interval_seconds: float = 0.25,
    device_probe_retry_count: int = 0,
    clock: "_FakeClock | None" = None,
) -> SpotifyPlaybackBackend:
    return SpotifyPlaybackBackend(
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-token",
        target_device_name="jukebox",
        requester=requester,
        confirmation_timeout_seconds=confirmation_timeout_seconds,
        confirmation_poll_interval_seconds=confirmation_poll_interval_seconds,
        device_probe_retry_count=device_probe_retry_count,
        device_probe_retry_interval_seconds=0.0,
        clock=_FakeClock([0.0, 0.0]) if clock is None else clock,
        sleeper=lambda seconds: None,
    )


def _request(raw: str, kind: SpotifyUriKind) -> PlaybackRequest:
    return PlaybackRequest(uri=SpotifyUri(raw=raw, kind=kind, spotify_id=raw.rsplit(":", 1)[1]))


def _http_error(url: str, code: int, *, retry_after: int | None = None) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return HTTPError(url=url, code=code, msg="HTTP error", hdrs=headers, fp=None)


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


class _FakeClock:
    def __init__(self, values: list[float]) -> None:
        self._values = values
        self._last = values[-1]

    def __call__(self) -> float:
        if not self._values:
            return self._last
        self._last = self._values.pop(0)
        return self._last
