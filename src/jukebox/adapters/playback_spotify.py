"""Spotify playback backend using the Spotify Web API."""

from __future__ import annotations

import base64
import json
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


class SpotifyPlaybackBackend:
    """Dispatch playback commands to Spotify's player API."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        device_id: str | None = None,
        requester: Requester | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._device_id = device_id
        self._requester = _default_requester if requester is None else requester
        self._timeout_seconds = timeout_seconds

    def dispatch(self, request: PlaybackRequest) -> PlaybackResult:
        """Refresh an access token and send a playback command."""

        access_token_or_error = self._refresh_access_token()
        if isinstance(access_token_or_error, PlaybackResult):
            return access_token_or_error

        payload: dict[str, object]
        if request.uri.kind == "track":
            payload = {"uris": [request.uri.raw]}
        else:
            payload = {"context_uri": request.uri.raw}

        url = "https://api.spotify.com/v1/me/player/play"
        if self._device_id is not None:
            url = f"{url}?{urlencode({'device_id': self._device_id})}"

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
            return PlaybackResult(ok=True, backend="spotify", message="Playback dispatched.")
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
