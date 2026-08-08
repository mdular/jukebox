"""Tests for the Spotify Connect probe script."""

from __future__ import annotations

import json
import os
import sys
import unittest
from email.message import Message
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "spotify_connect_probe.py"
_SPEC = spec_from_file_location("spotify_connect_probe", _MODULE_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
_MODULE = module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

ProbeConfig = _MODULE.ProbeConfig
ResponseLike = _MODULE.ResponseLike
main = _MODULE.main
run_probe = _MODULE.run_probe


class SpotifyConnectProbeTests(unittest.TestCase):
    def test_probe_uses_direct_play_first_for_track_uris(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(200, {"devices": [{"id": "device-id", "name": "jukebox"}]}),
                _FakeResponse(204, None),
                _FakeResponse(204, None),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "device-id", "name": "jukebox"},
                        "is_playing": True,
                        "item": {"uri": "spotify:track:abc123"},
                    },
                ),
            ]
        )

        result = run_probe(
            ProbeConfig(
                client_id="client-id",
                client_secret="client-secret",
                refresh_token="refresh-token",
                target_device_name="jukebox",
                uri="spotify:track:abc123",
            ),
            requester=requester,
        )

        self.assertEqual(result["result"], "ok")
        play_request = requester.requests[3]
        self.assertEqual(
            json.loads(play_request.data.decode("utf-8")),
            {"uris": ["spotify:track:abc123"]},
        )
        self.assertEqual(
            play_request.full_url,
            "https://api.spotify.com/v1/me/player/play?device_id=device-id",
        )

    def test_probe_transfers_and_retries_when_direct_play_fails(self) -> None:
        requester = _SequenceRequester(
            [
                _FakeResponse(200, {"access_token": "access-token"}),
                _FakeResponse(200, {"devices": [{"id": "device-id", "name": "jukebox"}]}),
                _FakeResponse(204, None),
                _http_error("https://api.spotify.com/v1/me/player/play?device_id=device-id", 404),
                _FakeResponse(204, None),
                _FakeResponse(204, None),
                _FakeResponse(
                    200,
                    {
                        "device": {"id": "device-id", "name": "jukebox"},
                        "is_playing": True,
                        "item": {"uri": "spotify:track:abc123"},
                    },
                ),
            ]
        )

        result = run_probe(
            ProbeConfig(
                client_id="client-id",
                client_secret="client-secret",
                refresh_token="refresh-token",
                target_device_name="jukebox",
                uri="spotify:track:abc123",
            ),
            requester=requester,
        )

        self.assertEqual(result["result"], "ok")
        transfer_request = requester.requests[4]
        retry_request = requester.requests[5]
        self.assertEqual(transfer_request.full_url, "https://api.spotify.com/v1/me/player")
        self.assertEqual(
            json.loads(transfer_request.data.decode("utf-8")),
            {"device_ids": ["device-id"], "play": False},
        )
        self.assertEqual(
            retry_request.full_url,
            "https://api.spotify.com/v1/me/player/play?device_id=device-id",
        )

    def test_main_requires_env_credentials_and_target(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(main(["spotify:track:abc123"]), 2)


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


def _http_error(url: str, code: int) -> HTTPError:
    return HTTPError(url=url, code=code, msg="HTTP error", hdrs=Message(), fp=None)
