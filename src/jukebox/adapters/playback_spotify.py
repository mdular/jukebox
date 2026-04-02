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
from ..runtime_health import DependencyStatus


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

    def status(self) -> DependencyStatus:
        """Return the current Spotify readiness status."""

        access_token_or_error = self._refresh_access_token()
        if isinstance(access_token_or_error, PlaybackResult):
            return self._status_from_result(access_token_or_error)

        target_device_or_error = self._resolve_target_device(access_token_or_error)
        if isinstance(target_device_or_error, PlaybackResult):
            return self._status_from_result(target_device_or_error)

        return DependencyStatus(
            code="ready",
            ready=True,
            message="waiting for scan input",
            backend="spotify",
            device_name=target_device_or_error.name,
        )

    def dispatch(self, request: PlaybackRequest) -> PlaybackResult:
        """Refresh an access token, transfer playback, and confirm it started."""

        access_token_or_error = self._refresh_access_token()
        if isinstance(access_token_or_error, PlaybackResult):
            return access_token_or_error

        last_result: PlaybackResult | None = None
        for attempt in range(2):
            target_device_or_error = self._resolve_target_device(access_token_or_error)
            if isinstance(target_device_or_error, PlaybackResult):
                if target_device_or_error.reason_code == "device_not_listed" and attempt == 0:
                    last_result = target_device_or_error
                    continue
                return target_device_or_error

            transfer_result = self._transfer_playback(access_token_or_error, target_device_or_error)
            if not transfer_result.ok:
                if transfer_result.reason_code == "connect_transfer_failed" and attempt == 0:
                    last_result = transfer_result
                    continue
                return transfer_result

            play_result = self._start_playback(
                access_token_or_error,
                target_device_or_error,
                request,
            )
            if not play_result.ok:
                return play_result

            return self._confirm_playback(access_token_or_error, target_device_or_error, request)

        assert last_result is not None
        return last_result

    def enqueue(self, request: PlaybackRequest) -> PlaybackResult:
        """Queue one track on the target device."""

        if request.uri.kind != "track":
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="unsupported_content",
                message="Spotify queue only supports track URIs.",
            )

        access_token_or_error = self._refresh_access_token()
        if isinstance(access_token_or_error, PlaybackResult):
            return access_token_or_error

        target_device_or_error = self._resolve_target_device(access_token_or_error)
        if isinstance(target_device_or_error, PlaybackResult):
            return target_device_or_error

        return self._device_command(
            access_token_or_error,
            target_device_or_error,
            path="queue",
            method="POST",
            query={"uri": request.uri.raw, "device_id": target_device_or_error.device_id},
            operation="queue",
        )

    def stop(self) -> PlaybackResult:
        """Pause playback on the target device."""

        access_token_or_error = self._refresh_access_token()
        if isinstance(access_token_or_error, PlaybackResult):
            return access_token_or_error

        target_device_or_error = self._resolve_target_device(access_token_or_error)
        if isinstance(target_device_or_error, PlaybackResult):
            return target_device_or_error

        return self._device_command(
            access_token_or_error,
            target_device_or_error,
            path="pause",
            method="PUT",
            query={"device_id": target_device_or_error.device_id},
            operation="pause",
        )

    def skip_next(self) -> PlaybackResult:
        """Advance to the next track on the target device."""

        access_token_or_error = self._refresh_access_token()
        if isinstance(access_token_or_error, PlaybackResult):
            return access_token_or_error

        target_device_or_error = self._resolve_target_device(access_token_or_error)
        if isinstance(target_device_or_error, PlaybackResult):
            return target_device_or_error

        return self._device_command(
            access_token_or_error,
            target_device_or_error,
            path="next",
            method="POST",
            query={"device_id": target_device_or_error.device_id},
            operation="next",
        )

    def set_volume_percent(self, percent: int) -> PlaybackResult:
        """Apply a volume preset percentage on the target device."""

        if percent < 0 or percent > 100:
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="volume_control_unavailable",
                message="Spotify volume percent must be between 0 and 100.",
            )

        access_token_or_error = self._refresh_access_token()
        if isinstance(access_token_or_error, PlaybackResult):
            return access_token_or_error

        target_device_or_error = self._resolve_target_device(access_token_or_error)
        if isinstance(target_device_or_error, PlaybackResult):
            return target_device_or_error

        return self._device_command(
            access_token_or_error,
            target_device_or_error,
            path="volume",
            method="PUT",
            query={
                "volume_percent": str(percent),
                "device_id": target_device_or_error.device_id,
            },
            operation="volume",
        )

    def player_active(self) -> bool | None:
        """Return whether the target device is actively playing."""

        access_token_or_error = self._refresh_access_token()
        if isinstance(access_token_or_error, PlaybackResult):
            return None

        target_device_or_error = self._resolve_target_device(access_token_or_error)
        if isinstance(target_device_or_error, PlaybackResult):
            return None

        state_or_error = self._get_current_playback(access_token_or_error)
        if isinstance(state_or_error, PlaybackResult):
            return None
        if state_or_error is None:
            return False

        device = state_or_error.get("device")
        if not isinstance(device, dict):
            return None
        if device.get("id") != target_device_or_error.device_id:
            return False
        return bool(state_or_error.get("is_playing") is True)

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
                reason_code="spotify_api_auth_error",
                message=f"Spotify authentication failed with HTTP {exc.code}.",
            )
        except URLError as exc:
            return self._network_error(exc)

        try:
            body = response.read().decode("utf-8")
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_api_auth_error",
                message="Spotify token refresh returned invalid JSON.",
            )

        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or access_token == "":
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_api_auth_error",
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
            return self._map_http_error(exc, operation="device_lookup")
        except URLError as exc:
            return self._network_error(exc)

        if response.status != 200:
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="network_discovery_failed",
                message=f"Unexpected Spotify response status: {response.status}.",
            )

        try:
            payload = json.loads(response.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="network_discovery_failed",
                message="Spotify devices response returned invalid JSON.",
            )

        devices = payload.get("devices")
        if not isinstance(devices, list):
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="network_discovery_failed",
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
            reason_code="device_not_listed",
            message="Spotify target device unavailable.",
            device_name=self._target_device_name,
        )

    def _transfer_playback(self, access_token: str, target_device: _TargetDevice) -> PlaybackResult:
        transfer_request = Request(
            "https://api.spotify.com/v1/me/player",
            data=json.dumps(
                {"device_ids": [target_device.device_id], "play": False}
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="PUT",
        )

        try:
            response = self._requester(transfer_request, self._timeout_seconds)
        except HTTPError as exc:
            result = self._map_http_error(exc, operation="transfer")
            return PlaybackResult(
                ok=False,
                backend=result.backend,
                reason_code=result.reason_code,
                message=result.message,
                device_name=target_device.name,
            )
        except URLError as exc:
            result = self._network_error(exc)
            return PlaybackResult(
                ok=False,
                backend=result.backend,
                reason_code=result.reason_code,
                message=result.message,
                device_name=target_device.name,
            )

        if 200 <= response.status < 300:
            return PlaybackResult(ok=True, backend="spotify", device_name=target_device.name)
        return PlaybackResult(
            ok=False,
            backend="spotify",
            reason_code="connect_transfer_failed",
            message=f"Unexpected Spotify response status: {response.status}.",
            device_name=target_device.name,
        )

    def _start_playback(
        self,
        access_token: str,
        target_device: _TargetDevice,
        request: PlaybackRequest,
    ) -> PlaybackResult:
        payload: dict[str, object]
        if request.uri.kind == "track":
            payload = {"uris": [request.uri.raw]}
        else:
            payload = {"context_uri": request.uri.raw}

        url = "https://api.spotify.com/v1/me/player/play"
        url = f"{url}?{urlencode({'device_id': target_device.device_id})}"
        play_request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="PUT",
        )

        try:
            response = self._requester(play_request, self._timeout_seconds)
        except HTTPError as exc:
            result = self._map_http_error(exc, operation="start")
            return PlaybackResult(
                ok=False,
                backend=result.backend,
                reason_code=result.reason_code,
                message=result.message,
                device_name=target_device.name,
            )
        except URLError as exc:
            result = self._network_error(exc)
            return PlaybackResult(
                ok=False,
                backend=result.backend,
                reason_code=result.reason_code,
                message=result.message,
                device_name=target_device.name,
            )

        if 200 <= response.status < 300:
            return PlaybackResult(ok=True, backend="spotify", device_name=target_device.name)
        return PlaybackResult(
            ok=False,
            backend="spotify",
            reason_code="spotify_start_failed",
            message=f"Unexpected Spotify response status: {response.status}.",
            device_name=target_device.name,
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

    def _device_command(
        self,
        access_token: str,
        target_device: _TargetDevice,
        *,
        path: str,
        method: str,
        query: dict[str, str],
        operation: str,
    ) -> PlaybackResult:
        url = f"https://api.spotify.com/v1/me/player/{path}?{urlencode(query)}"
        command_request = Request(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            method=method,
        )

        try:
            response = self._requester(command_request, self._timeout_seconds)
        except HTTPError as exc:
            result = self._map_http_error(exc, operation=operation)
            return PlaybackResult(
                ok=False,
                backend=result.backend,
                reason_code=result.reason_code,
                message=result.message,
                device_name=target_device.name,
            )
        except URLError as exc:
            result = self._network_error(exc)
            return PlaybackResult(
                ok=False,
                backend=result.backend,
                reason_code=result.reason_code,
                message=result.message,
                device_name=target_device.name,
            )

        if 200 <= response.status < 300:
            return PlaybackResult(ok=True, backend="spotify", device_name=target_device.name)
        return PlaybackResult(
            ok=False,
            backend="spotify",
            reason_code=self._reason_code_for_operation(operation),
            message=f"Unexpected Spotify response status: {response.status}.",
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
            return self._map_http_error(exc, operation="confirm")
        except URLError as exc:
            return self._network_error(exc)

        if response.status == 204:
            return None
        if response.status != 200:
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="network_discovery_failed",
                message=f"Unexpected Spotify response status: {response.status}.",
            )

        try:
            payload = json.loads(response.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="network_discovery_failed",
                message="Spotify playback status returned invalid JSON.",
            )
        if not isinstance(payload, dict):
            return PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="network_discovery_failed",
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

    def _map_http_error(self, exc: HTTPError, *, operation: str) -> PlaybackResult:
        if exc.code in {401, 403}:
            reason_code = "spotify_api_auth_error"
        elif exc.code == 429:
            reason_code = "spotify_rate_limited"
        elif operation == "transfer":
            reason_code = "connect_transfer_failed"
        elif operation == "start":
            reason_code = "spotify_start_failed"
        elif operation in {"pause", "next"} and exc.code == 404:
            reason_code = "no_active_playback"
        elif operation == "volume" and exc.code in {403, 404}:
            reason_code = "volume_control_unavailable"
        elif operation == "queue":
            reason_code = "spotify_queue_failed"
        else:
            reason_code = self._reason_code_for_operation(operation)
        return PlaybackResult(
            ok=False,
            backend="spotify",
            reason_code=reason_code,
            message=f"Spotify playback failed with HTTP {exc.code}.",
        )

    def _network_error(self, exc: URLError) -> PlaybackResult:
        return PlaybackResult(
            ok=False,
            backend="spotify",
            reason_code="network_discovery_failed",
            message=f"Spotify transport error: {exc.reason}",
        )

    def _status_from_result(self, result: PlaybackResult) -> DependencyStatus:
        if result.reason_code == "spotify_api_auth_error":
            code = "controller_auth_unavailable"
        elif result.reason_code == "device_not_listed":
            code = "receiver_unavailable"
        else:
            code = "network_unavailable"
        return DependencyStatus(
            code=code,
            ready=False,
            message=result.message or "dependency unavailable",
            reason_code=result.reason_code,
            backend=result.backend,
            device_name=result.device_name,
        )

    def _reason_code_for_operation(self, operation: str) -> str:
        if operation == "start":
            return "spotify_start_failed"
        if operation == "queue":
            return "spotify_queue_failed"
        if operation == "pause":
            return "no_active_playback"
        if operation == "next":
            return "no_active_playback"
        if operation == "volume":
            return "volume_control_unavailable"
        return "network_discovery_failed"


def _default_requester(request: Request, timeout_seconds: float) -> ResponseLike:
    response = urlopen(request, timeout=timeout_seconds)
    return cast(ResponseLike, response)
