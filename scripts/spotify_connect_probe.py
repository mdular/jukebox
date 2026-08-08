#!/usr/bin/env python3
"""Probe Spotify Connect handoff behavior for one requested URI."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from dataclasses import dataclass
from typing import Callable, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ResponseLike(Protocol):
    """Minimal HTTP response contract used by the probe."""

    status: int

    def read(self) -> bytes:
        """Return the full response body."""


Requester = Callable[[Request, float], ResponseLike]


@dataclass(frozen=True)
class ProbeConfig:
    client_id: str
    client_secret: str
    refresh_token: str
    uri: str
    device_id: str | None = None
    target_device_name: str | None = None
    timeout_seconds: float = 5.0


def main(argv: list[str] | None = None) -> int:
    """Run the Spotify Connect probe."""

    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        config = _config_from_env(uri=args.uri)
        payload = run_probe(config)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def run_probe(config: ProbeConfig, requester: Requester | None = None) -> dict[str, object]:
    """Run the probe and return a JSON-serializable summary."""

    request = _default_requester if requester is None else requester
    uri_kind = _spotify_uri_kind(config.uri)
    token = _refresh_access_token(config, request)
    target = _resolve_target_device(config, token, request)
    preflight = _current_playback(token, request, config.timeout_seconds)

    direct_result = _play(
        uri=config.uri,
        uri_kind=uri_kind,
        device_id=target["id"],
        access_token=token,
        requester=request,
        timeout_seconds=config.timeout_seconds,
    )

    transfer_result: dict[str, object] | None = None
    retry_result: dict[str, object] | None = None
    if not direct_result["ok"]:
        transfer_result = _transfer_playback(
            device_id=target["id"],
            access_token=token,
            requester=request,
            timeout_seconds=config.timeout_seconds,
        )
        if transfer_result["ok"]:
            retry_result = _play(
                uri=config.uri,
                uri_kind=uri_kind,
                device_id=target["id"],
                access_token=token,
                requester=request,
                timeout_seconds=config.timeout_seconds,
            )

    post_play = _current_playback(token, request, config.timeout_seconds)
    final_ok = bool(
        direct_result["ok"] or (transfer_result is not None and transfer_result["ok"] and retry_result and retry_result["ok"])
    )
    return {
        "uri": config.uri,
        "uri_kind": uri_kind,
        "target_device": target,
        "preflight": preflight,
        "direct_play": direct_result,
        "transfer": transfer_result,
        "retry_play": retry_result,
        "post_play": post_play,
        "result": "ok" if final_ok else "failed",
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe direct-play-first Spotify Connect handoff for one URI."
    )
    parser.add_argument("uri", help="Spotify track, album, or playlist URI to probe")
    return parser.parse_args(argv)


def _config_from_env(*, uri: str) -> ProbeConfig:
    client_id = os.environ.get("JUKEBOX_SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("JUKEBOX_SPOTIFY_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("JUKEBOX_SPOTIFY_REFRESH_TOKEN", "").strip()
    device_id = os.environ.get("JUKEBOX_SPOTIFY_DEVICE_ID", "").strip() or None
    target_device_name = os.environ.get("JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME", "").strip() or None

    missing = [
        key
        for key, value in (
            ("JUKEBOX_SPOTIFY_CLIENT_ID", client_id),
            ("JUKEBOX_SPOTIFY_CLIENT_SECRET", client_secret),
            ("JUKEBOX_SPOTIFY_REFRESH_TOKEN", refresh_token),
        )
        if value == ""
    ]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    if device_id is None and target_device_name is None:
        raise ValueError(
            "Set JUKEBOX_SPOTIFY_DEVICE_ID or JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME for probe routing."
        )

    return ProbeConfig(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        uri=uri,
        device_id=device_id,
        target_device_name=target_device_name,
    )


def _refresh_access_token(config: ProbeConfig, requester: Requester) -> str:
    credentials = f"{config.client_id}:{config.client_secret}".encode("utf-8")
    encoded_credentials = base64.b64encode(credentials).decode("ascii")
    token_request = Request(
        "https://accounts.spotify.com/api/token",
        data=urlencode(
            {"grant_type": "refresh_token", "refresh_token": config.refresh_token}
        ).encode("ascii"),
        headers={
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    response = _perform_request(token_request, requester, config.timeout_seconds)
    if not response["ok"]:
        raise RuntimeError(f"Token refresh failed: {response['message']}")

    payload = response["json"]
    assert isinstance(payload, dict)
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or access_token == "":
        raise RuntimeError("Token refresh did not return an access token.")
    return access_token


def _resolve_target_device(
    config: ProbeConfig,
    access_token: str,
    requester: Requester,
) -> dict[str, str]:
    devices_request = Request(
        "https://api.spotify.com/v1/me/player/devices",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    response = _perform_request(devices_request, requester, config.timeout_seconds)
    if not response["ok"]:
        raise RuntimeError(f"Device lookup failed: {response['message']}")

    payload = response["json"]
    assert isinstance(payload, dict)
    devices = payload.get("devices")
    if not isinstance(devices, list):
        raise RuntimeError("Spotify devices response did not include a device list.")

    for device in devices:
        if not isinstance(device, dict):
            continue
        device_id = device.get("id")
        device_name = device.get("name")
        if not isinstance(device_id, str) or not isinstance(device_name, str):
            continue
        if config.device_id is not None and device_id != config.device_id:
            continue
        if config.device_id is None and device_name != config.target_device_name:
            continue
        return {"id": device_id, "name": device_name}

    raise RuntimeError("Configured Spotify target device is not listed.")


def _current_playback(
    access_token: str,
    requester: Requester,
    timeout_seconds: float,
) -> dict[str, object]:
    playback_request = Request(
        "https://api.spotify.com/v1/me/player",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    response = _perform_request(playback_request, requester, timeout_seconds)
    return {
        "ok": response["ok"],
        "status": response["status"],
        "json": response["json"],
        "message": response["message"],
    }


def _play(
    *,
    uri: str,
    uri_kind: str,
    device_id: str,
    access_token: str,
    requester: Requester,
    timeout_seconds: float,
) -> dict[str, object]:
    if uri_kind == "track":
        payload = {"uris": [uri]}
    else:
        payload = {"context_uri": uri}
    play_request = Request(
        f"https://api.spotify.com/v1/me/player/play?{urlencode({'device_id': device_id})}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    response = _perform_request(play_request, requester, timeout_seconds)
    return {
        "ok": response["ok"],
        "status": response["status"],
        "message": response["message"],
        "payload": payload,
    }


def _transfer_playback(
    *,
    device_id: str,
    access_token: str,
    requester: Requester,
    timeout_seconds: float,
) -> dict[str, object]:
    transfer_request = Request(
        "https://api.spotify.com/v1/me/player",
        data=json.dumps({"device_ids": [device_id], "play": False}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    response = _perform_request(transfer_request, requester, timeout_seconds)
    return {
        "ok": response["ok"],
        "status": response["status"],
        "message": response["message"],
    }


def _perform_request(
    request: Request,
    requester: Requester,
    timeout_seconds: float,
) -> dict[str, object]:
    try:
        response = requester(request, timeout_seconds)
    except HTTPError as exc:
        return {
            "ok": False,
            "status": exc.code,
            "json": _decode_json(exc),
            "message": f"HTTP {exc.code}",
        }
    except URLError as exc:
        return {
            "ok": False,
            "status": None,
            "json": None,
            "message": f"transport error: {exc.reason}",
        }

    payload = _decode_json(response)
    if 200 <= response.status < 300:
        return {
            "ok": True,
            "status": response.status,
            "json": payload,
            "message": "ok",
        }
    return {
        "ok": False,
        "status": response.status,
        "json": payload,
        "message": f"unexpected status {response.status}",
    }


def _decode_json(response: ResponseLike) -> dict[str, object] | list[object] | None:
    body = response.read()
    if body == b"":
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if isinstance(payload, (dict, list)):
        return payload
    return None


def _spotify_uri_kind(uri: str) -> str:
    parts = uri.split(":")
    if len(parts) != 3 or parts[0] != "spotify" or parts[1] not in {"track", "album", "playlist"}:
        raise ValueError("URI must be a spotify:track, spotify:album, or spotify:playlist value.")
    return parts[1]


def _default_requester(request: Request, timeout_seconds: float) -> ResponseLike:
    response = urlopen(request, timeout=timeout_seconds)
    return cast(ResponseLike, response)


if __name__ == "__main__":
    raise SystemExit(main())
