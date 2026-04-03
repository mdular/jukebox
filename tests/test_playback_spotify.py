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
from jukebox.core.cards import SpotifyUriKind
from jukebox.core.models import PlaybackRequest, SpotifyUri


class SpotifyPlaybackBackendTests(unittest.TestCase):
    def test_status_is_ready_when_auth_and_target_are_available(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
            ]
        )
        backend = _backend(requester=requester)

        status = backend.status()

        self.assertTrue(status.ready)
        self.assertEqual(status.code, "ready")
        self.assertEqual(status.device_name, "jukebox")
        self.assertEqual(requester.requests[0].full_url, "https://accounts.spotify.com/api/token")
        self.assertEqual(requester.requests[1].full_url, "https://api.spotify.com/v1/me/player/devices")

    def test_status_reports_controller_auth_unavailable(self) -> None:
        requester = _SequenceRequester([_http_error("https://accounts.spotify.com/api/token", 401)])
        backend = _backend(requester=requester)

        status = backend.status()

        self.assertFalse(status.ready)
        self.assertEqual(status.code, "controller_auth_unavailable")
        self.assertEqual(status.reason_code, "spotify_api_auth_error")

    def test_status_reports_network_unavailable_for_transport_failures(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                URLError("network down"),
            ]
        )
        backend = _backend(requester=requester)

        status = backend.status()

        self.assertFalse(status.ready)
        self.assertEqual(status.code, "network_unavailable")
        self.assertEqual(status.reason_code, "network_discovery_failed")

    def test_status_reports_receiver_unavailable_when_target_is_not_listed(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(200, {"devices": [{"id": "other-device", "name": "kitchen"}]}),
            ]
        )
        backend = _backend(requester=requester)

        status = backend.status()

        self.assertFalse(status.ready)
        self.assertEqual(status.code, "receiver_unavailable")
        self.assertEqual(status.reason_code, "device_not_listed")
        self.assertEqual(status.device_name, "jukebox")

    def test_dispatch_transfers_playback_then_starts_track_and_confirms(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
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
        self.assertEqual(result.device_name, "jukebox")
        token_request, devices_request, transfer_request, play_request, state_request = (
            requester.requests
        )
        expected_basic = base64.b64encode(b"client-id:client-secret").decode("ascii")
        self.assertEqual(token_request.get_header("Authorization"), f"Basic {expected_basic}")
        self.assertEqual(devices_request.full_url, "https://api.spotify.com/v1/me/player/devices")
        self.assertEqual(transfer_request.full_url, "https://api.spotify.com/v1/me/player")
        self.assertEqual(
            json.loads(cast(bytes, transfer_request.data).decode("utf-8")),
            {"device_ids": ["device-id"], "play": False},
        )
        self.assertEqual(
            play_request.full_url,
            "https://api.spotify.com/v1/me/player/play?device_id=device-id",
        )
        self.assertEqual(
            json.loads(cast(bytes, play_request.data).decode("utf-8")),
            {"uris": ["spotify:track:6rqhFgbbKwnb9MLmUQDhG6"]},
        )
        self.assertEqual(state_request.full_url, "https://api.spotify.com/v1/me/player")

    def test_context_dispatch_uses_context_uri_payload(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
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
        play_request = requester.requests[3]
        self.assertEqual(
            json.loads(cast(bytes, play_request.data).decode("utf-8")),
            {"context_uri": "spotify:album:1ATL5GLyefJaxhQzSPVrLX"},
        )

    def test_dispatch_refetches_devices_on_each_dispatch(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token-1"}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-a", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
                _FakeResponse(204, None),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "device-a", "name": "jukebox"},
                        "is_playing": True,
                        "item": {"uri": "spotify:track:1111111111111111111111"},
                    },
                ),
                _FakeResponse(200, {"access_token": "access-token-2"}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-b", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
                _FakeResponse(204, None),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "device-b", "name": "jukebox"},
                        "is_playing": True,
                        "item": {"uri": "spotify:track:2222222222222222222222"},
                    },
                ),
            ]
        )
        backend = _backend(requester=requester)

        first = backend.dispatch(_request("spotify:track:1111111111111111111111", "track"))
        second = backend.dispatch(_request("spotify:track:2222222222222222222222", "track"))

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        play_urls = [
            request.full_url
            for request in requester.requests
            if request.full_url.startswith("https://api.spotify.com/v1/me/player/play")
        ]
        self.assertEqual(
            play_urls,
            [
                "https://api.spotify.com/v1/me/player/play?device_id=device-a",
                "https://api.spotify.com/v1/me/player/play?device_id=device-b",
            ],
        )

    def test_dispatch_retries_when_target_is_not_listed_initially(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(200, {"devices": []}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
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
        device_requests = [
            request.full_url
            for request in requester.requests
            if request.full_url == "https://api.spotify.com/v1/me/player/devices"
        ]
        self.assertEqual(len(device_requests), 2)

    def test_dispatch_retries_once_after_transfer_failure(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _http_error("https://api.spotify.com/v1/me/player", 404),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
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
        transfer_requests = [
            request.full_url for request in requester.requests if request.full_url == "https://api.spotify.com/v1/me/player"
        ]
        self.assertEqual(len(transfer_requests), 3)

    def test_dispatch_returns_device_not_listed_after_retry_exhausted(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(200, {"devices": []}),
                _FakeResponse(200, {"devices": []}),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.dispatch(_request("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "track"))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "device_not_listed")

    def test_dispatch_reports_network_discovery_failure(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                URLError("network down"),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.dispatch(_request("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "track"))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "network_discovery_failed")

    def test_dispatch_times_out_when_playback_is_not_confirmed(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
                _FakeResponse(204, None),
                _FakeResponse(
                    200,
                    {"device": {"id": "device-id", "name": "jukebox"}, "is_playing": False},
                ),
                _FakeResponse(
                    200,
                    {"device": {"id": "device-id", "name": "jukebox"}, "is_playing": False},
                ),
            ]
        )
        backend = _backend(
            requester=requester,
            confirmation_timeout_seconds=0.5,
            confirmation_poll_interval_seconds=0.25,
            clock=_FakeClock([0.0, 0.0, 0.25, 0.5]),
        )

        result = backend.dispatch(_request("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "track"))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "spotify_start_not_confirmed")

    def test_dispatch_accepts_playing_target_device_when_spotify_metadata_is_stale(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
                _FakeResponse(204, None),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "device-id", "name": "jukebox"},
                        "is_playing": True,
                        "item": {"uri": "spotify:track:previous-track"},
                    },
                ),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "device-id", "name": "jukebox"},
                        "is_playing": True,
                        "item": {"uri": "spotify:track:previous-track"},
                    },
                ),
            ]
        )
        backend = _backend(
            requester=requester,
            confirmation_timeout_seconds=0.5,
            confirmation_poll_interval_seconds=0.25,
            clock=_FakeClock([0.0, 0.0, 0.25, 0.5]),
        )

        result = backend.dispatch(_request("spotify:track:6rqhFgbbKwnb9MLmUQDhG6", "track"))

        self.assertTrue(result.ok)
        self.assertEqual(result.device_name, "jukebox")
        self.assertEqual(
            result.message,
            (
                "Playback started, but Spotify did not report the requested item "
                "before confirmation timed out."
            ),
        )

    def test_enqueue_calls_queue_endpoint(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
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
        queue_request = requester.requests[2]
        self.assertEqual(
            queue_request.full_url,
            "https://api.spotify.com/v1/me/player/queue?uri=spotify%3Atrack%3A6rqhFgbbKwnb9MLmUQDhG6&device_id=device-id",
        )

    def test_stop_calls_pause_endpoint(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.stop()

        self.assertTrue(result.ok)
        self.assertEqual(
            requester.requests[2].full_url,
            "https://api.spotify.com/v1/me/player/pause?device_id=device-id",
        )

    def test_skip_next_calls_next_endpoint(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.skip_next()

        self.assertTrue(result.ok)
        self.assertEqual(
            requester.requests[2].full_url,
            "https://api.spotify.com/v1/me/player/next?device_id=device-id",
        )

    def test_set_volume_percent_calls_volume_endpoint(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(
                    200,
                    {"devices": [{"id": "device-id", "name": "jukebox", "is_active": True}]},
                ),
                _FakeResponse(204, None),
            ]
        )
        backend = _backend(requester=requester)

        result = backend.set_volume_percent(55)

        self.assertTrue(result.ok)
        self.assertEqual(
            requester.requests[2].full_url,
            "https://api.spotify.com/v1/me/player/volume?volume_percent=55&device_id=device-id",
        )

    def test_player_active_reports_true_for_matching_playback(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(
                    200,
                    {
                        "devices": [{"id": "device-id", "name": "jukebox", "is_active": True}],
                    },
                ),
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

        self.assertTrue(backend.player_active())

    def test_player_active_reports_false_when_no_playback_is_active(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(
                    200,
                    {
                        "devices": [{"id": "device-id", "name": "jukebox", "is_active": True}],
                    },
                ),
                _FakeResponse(204, None),
            ]
        )
        backend = _backend(requester=requester)

        self.assertFalse(backend.player_active())


def _backend(
    *,
    requester: _SequenceRequester,
    confirmation_timeout_seconds: float = 5.0,
    confirmation_poll_interval_seconds: float = 0.25,
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
        clock=_FakeClock([0.0, 0.0]) if clock is None else clock,
        sleeper=lambda seconds: None,
    )


def _request(raw: str, kind: SpotifyUriKind) -> PlaybackRequest:
    return PlaybackRequest(uri=SpotifyUri(raw=raw, kind=kind, spotify_id=raw.rsplit(":", 1)[1]))


def _http_error(url: str, code: int) -> HTTPError:
    return HTTPError(url=url, code=code, msg="HTTP error", hdrs=Message(), fp=None)


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
