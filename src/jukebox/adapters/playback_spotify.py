"""Spotify playback backend using the Spotify Web API."""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Callable, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..core.models import PlaybackRequest, PlaybackResult


class ResponseLike(Protocol):
    """Minimal HTTP response contract used by the backend."""

    status: int

    def read(self) -> bytes:
        """Return the full response body."""


Requester = Callable[[Request, float], ResponseLike]
Clock = Callable[[], float]
Sleeper = Callable[[float], None]


@dataclass(frozen=True)
class _TargetDevice:
    device_id: str
    name: str


class SpotifyPlaybackBackend:
    """Dispatch playback commands to Spotify's player API."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        device_id: str | None = None,
        target_device_name: str | None = None,
        requester: Requester | None = None,
        timeout_seconds: float = 5.0,
        confirmation_timeout_seconds: float = 5.0,
        confirmation_poll_interval_seconds: float = 0.25,
        clock: Clock | None = None,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._device_id = device_id
        self._target_device_name = target_device_name
        self._requester = _default_requester if requester is None else requester
        self._timeout_seconds = timeout_seconds
        self._confirmation_timeout_seconds = confirmation_timeout_seconds
        self._confirmation_poll_interval_seconds = confirmation_poll_interval_seconds
        self._clock = time.monotonic if clock is None else clock
        self._sleeper = time.sleep if sleeper is None else sleeper

    def probe(self) -> PlaybackResult:
        """Validate Spotify auth for startup checks."""

        access_token_or_error = self._refresh_access_token()
        if isinstance(access_token_or_error, PlaybackResult):
            return access_token_or_error

        return PlaybackResult(
            ok=True,
            backend="spotify",
            message="Spotify authentication available.",
        )

    def dispatch(self, request: PlaybackRequest) -> PlaybackResult:
        """Refresh an access token, send playback, and confirm it started."""

        access_token_or_error = self._refresh_access_token()
        if isinstance(access_token_or_error, PlaybackResult):
            return access_token_or_error

        target_device_or_error = self._resolve_target_device(access_token_or_error)
        if isinstance(target_device_or_error, PlaybackResult):
            return target_device_or_error

        payload: dict[str, object]
        if request.uri.kind == "track":
            payload = {"uris": [request.uri.raw]}
        else:
            payload = {"context_uri": request.uri.raw}

        url = "https://api.spotify.com/v1/me/player/play"
        url = f"{url}?{urlencode({'device_id': target_device_or_error.device_id})}"

        http_request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token_or_error}",
                "Content-Type": "application/json",
            },
            method="PUT",
        )

        try:
            response = self._requester(http_request, self._timeout_seconds)
        except HTTPError as exc:
            return self._map_http_error(exc)
        except URLError as exc:
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_transport_error",
                message=f"Spotify transport error: {exc.reason}",
            )

        if 200 <= response.status < 300:
            return self._confirm_playback(
                access_token_or_error,
                target_device_or_error,
                request,
            )
        return PlaybackResult(
            ok=False,
            backend="spotify",
            reason_code="spotify_unexpected_response",
            message=f"Unexpected Spotify response status: {response.status}",
        )

    def _refresh_access_token(self) -> str | PlaybackResult:
        credentials = f"{self._client_id}:{self._client_secret}".encode("utf-8")
        encoded_credentials = base64.b64encode(credentials).decode("ascii")
        token_request = Request(
            "https://accounts.spotify.com/api/token",
            data=urlencode(
                {"grant_type": "refresh_token", "refresh_token": self._refresh_token}
            ).encode("ascii"),
            headers={
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )

        try:
            response = self._requester(token_request, self._timeout_seconds)
        except HTTPError as exc:
            if exc.code == 429:
                return PlaybackResult(
                    ok=False,
                    backend="spotify",
                    reason_code="spotify_rate_limited",
                    message="Spotify token refresh was rate limited.",
                )
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_auth_error",
                message=f"Spotify authentication failed with HTTP {exc.code}.",
            )
        except URLError as exc:
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_transport_error",
                message=f"Spotify transport error: {exc.reason}",
            )

        try:
            body = response.read().decode("utf-8")
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_unexpected_response",
                message="Spotify token refresh returned invalid JSON.",
            )

        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or access_token == "":
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_unexpected_response",
                message="Spotify token refresh response did not include an access token.",
            )
        return access_token

    def _resolve_target_device(self, access_token: str) -> _TargetDevice | PlaybackResult:
        devices_request = Request(
            "https://api.spotify.com/v1/me/player/devices",
            headers={"Authorization": f"Bearer {access_token}"},
            method="GET",
        )

        try:
            response = self._requester(devices_request, self._timeout_seconds)
        except HTTPError as exc:
            return self._map_http_error(exc)
        except URLError as exc:
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_transport_error",
                message=f"Spotify transport error: {exc.reason}",
            )

        if response.status != 200:
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_unexpected_response",
                message=f"Unexpected Spotify response status: {response.status}",
            )

        try:
            payload = json.loads(response.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_unexpected_response",
                message="Spotify devices response returned invalid JSON.",
            )

        devices = payload.get("devices")
        if not isinstance(devices, list):
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_unexpected_response",
                message="Spotify devices response did not include a device list.",
            )

        for device in devices:
            if not isinstance(device, dict):
                continue
            raw_device_id = device.get("id")
            raw_name = device.get("name")
            if not isinstance(raw_device_id, str) or raw_device_id == "":
                continue
            if not isinstance(raw_name, str) or raw_name == "":
                continue
            if self._device_id is not None and raw_device_id != self._device_id:
                continue
            if self._device_id is None and raw_name != self._target_device_name:
                continue
            return _TargetDevice(device_id=raw_device_id, name=raw_name)

        return PlaybackResult(
            ok=False,
            backend="spotify",
            reason_code="spotify_target_device_unavailable",
            message="Spotify target device unavailable.",
            device_name=self._target_device_name,
        )

    def _confirm_playback(
        self,
        access_token: str,
        target_device: _TargetDevice,
        request: PlaybackRequest,
    ) -> PlaybackResult:
        deadline = self._clock() + self._confirmation_timeout_seconds
        while True:
            state_or_error = self._get_current_playback(access_token)
            if isinstance(state_or_error, PlaybackResult):
                return state_or_error
            if state_or_error is not None and self._matches_requested_playback(
                state_or_error, target_device, request
            ):
                return PlaybackResult(
                    ok=True,
                    backend="spotify",
                    message="Playback started.",
                    device_name=target_device.name,
                )

            now = self._clock()
            if now + self._confirmation_poll_interval_seconds >= deadline:
                break
            self._sleeper(self._confirmation_poll_interval_seconds)

        return PlaybackResult(
            ok=False,
            backend="spotify",
            reason_code="spotify_start_not_confirmed",
            message="Spotify playback start was not confirmed in time.",
            device_name=target_device.name,
        )

    def _get_current_playback(self, access_token: str) -> dict[str, object] | None | PlaybackResult:
        playback_request = Request(
            "https://api.spotify.com/v1/me/player",
            headers={"Authorization": f"Bearer {access_token}"},
            method="GET",
        )

        try:
            response = self._requester(playback_request, self._timeout_seconds)
        except HTTPError as exc:
            return self._map_http_error(exc)
        except URLError as exc:
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_transport_error",
                message=f"Spotify transport error: {exc.reason}",
            )

        if response.status == 204:
            return None
        if response.status != 200:
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_unexpected_response",
                message=f"Unexpected Spotify response status: {response.status}",
            )

        try:
            payload = json.loads(response.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_unexpected_response",
                message="Spotify playback status returned invalid JSON.",
            )
        if not isinstance(payload, dict):
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_unexpected_response",
                message="Spotify playback status returned an invalid payload.",
            )
        return payload

    def _matches_requested_playback(
        self,
        payload: dict[str, object],
        target_device: _TargetDevice,
        request: PlaybackRequest,
    ) -> bool:
        device = payload.get("device")
        if not isinstance(device, dict):
            return False
        if device.get("id") != target_device.device_id:
            return False
        if payload.get("is_playing") is not True:
            return False

        if request.uri.kind == "track":
            item = payload.get("item")
            return isinstance(item, dict) and item.get("uri") == request.uri.raw

        context = payload.get("context")
        return isinstance(context, dict) and context.get("uri") == request.uri.raw

    def _map_http_error(self, exc: HTTPError) -> PlaybackResult:
        if exc.code == 401:
            reason_code = "spotify_auth_error"
        elif exc.code == 403:
            reason_code = "spotify_forbidden"
        elif exc.code == 404:
            reason_code = "spotify_no_active_device"
        elif exc.code == 429:
            reason_code = "spotify_rate_limited"
        else:
            reason_code = "spotify_unexpected_response"
        return PlaybackResult(
            ok=False,
            backend="spotify",
            reason_code=reason_code,
            message=f"Spotify playback failed with HTTP {exc.code}.",
        )


def _default_requester(request: Request, timeout_seconds: float) -> ResponseLike:
    response = urlopen(request, timeout=timeout_seconds)
    return cast(ResponseLike, response)
