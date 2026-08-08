"""Tests for runtime assembly."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jukebox.config import from_env
from jukebox.core.models import PlaybackResult
from jukebox.idle_monitor import IdleMonitor
from jukebox.operator_server import OperatorHttpServer
from jukebox.operator_state import OperatorStateStore
from jukebox.runtime import StartupError, build_runtime
from jukebox.runtime_health import DependencyStatus


class BuildRuntimeTests(unittest.TestCase):
    def test_build_runtime_registers_idle_monitor_and_rich_status_surface(self) -> None:
        helper = _FakeSystemHelpers()
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = from_env(
                {
                    "JUKEBOX_ENV": "test",
                    "JUKEBOX_IDLE_SHUTDOWN_SECONDS": "300",
                    "JUKEBOX_OPERATOR_HTTP_PORT": "8081",
                    "JUKEBOX_OPERATOR_STATE_PATH": str(Path(temp_dir) / "state.json"),
                }
            )

            with patch("jukebox.runtime.CommandSystemHelpers", return_value=helper):
                runtime = build_runtime(settings, io.StringIO(""))

            self.assertTrue(any(isinstance(service, IdleMonitor) for service in runtime.services))
            self.assertTrue(any(isinstance(sink, IdleMonitor) for sink in runtime.event_sinks))

            operator_server = next(
                service for service in runtime.services if isinstance(service, OperatorHttpServer)
            )
            response = operator_server.handle_request("GET", "/status.json")

            payload = response.json_body
            assert payload is not None
            runtime_payload = payload["runtime"]
            assert isinstance(runtime_payload, dict)
            self.assertIn("enabled_actions", runtime_payload)
            self.assertIn("scanner", runtime_payload)
            self.assertIn("playback", runtime_payload)
            self.assertIn("setup", runtime_payload)
            self.assertIn("config", runtime_payload)
            self.assertIn("idle", runtime_payload)
            config_payload = runtime_payload["config"]
            assert isinstance(config_payload, dict)
            self.assertIn("wifi_rollback_timeout_seconds", config_payload)

    def test_succeeded_auth_status_clears_receiver_reauth_requested(self) -> None:
        helper = _FakeSystemHelpers(
            auth_status_payload={
                "state": "succeeded",
                "message": "receiver authentication completed",
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "state.json"
            settings = from_env(
                {
                    "JUKEBOX_ENV": "test",
                    "JUKEBOX_OPERATOR_STATE_PATH": str(state_path),
                }
            )
            operator_state = OperatorStateStore(state_path)
            operator_state.mark_receiver_reauth_requested(True)

            with patch("jukebox.runtime.CommandSystemHelpers", return_value=helper):
                runtime = build_runtime(settings, io.StringIO(""))

            operator_server = next(
                service for service in runtime.services if isinstance(service, OperatorHttpServer)
            )
            status_response = operator_server.handle_request("GET", "/status.json")
            auth_response = operator_server.handle_request("GET", "/auth")

            status_payload = status_response.json_body
            assert status_payload is not None
            runtime_payload = status_payload["runtime"]
            assert isinstance(runtime_payload, dict)
            self.assertFalse(runtime_payload["auth_required"])
            self.assertFalse(operator_state.load().receiver_reauth_requested)
            assert auth_response.text_body is not None
            self.assertIn("succeeded", auth_response.text_body)

    def test_incomplete_auth_status_keeps_receiver_reauth_requested(self) -> None:
        for auth_state in ("pending", "running", "failed"):
            with self.subTest(auth_state=auth_state):
                helper = _FakeSystemHelpers(
                    auth_status_payload={
                        "state": auth_state,
                        "message": f"auth state is {auth_state}",
                    }
                )
                with tempfile.TemporaryDirectory() as temp_dir:
                    state_path = Path(temp_dir) / "state.json"
                    settings = from_env(
                        {
                            "JUKEBOX_ENV": "test",
                            "JUKEBOX_OPERATOR_STATE_PATH": str(state_path),
                        }
                    )
                    operator_state = OperatorStateStore(state_path)
                    operator_state.mark_receiver_reauth_requested(True)

                    with patch("jukebox.runtime.CommandSystemHelpers", return_value=helper):
                        runtime = build_runtime(settings, io.StringIO(""))

                    operator_server = next(
                        service
                        for service in runtime.services
                        if isinstance(service, OperatorHttpServer)
                    )
                    status_response = operator_server.handle_request("GET", "/status.json")

                    status_payload = status_response.json_body
                    assert status_payload is not None
                    runtime_payload = status_payload["runtime"]
                    assert isinstance(runtime_payload, dict)
                    self.assertTrue(runtime_payload["auth_required"])
                    self.assertTrue(operator_state.load().receiver_reauth_requested)

    def test_build_runtime_calls_playback_probe(self) -> None:
        helper = _FakeSystemHelpers()
        playback = _FakePlaybackBackend()
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = from_env(
                {
                    "JUKEBOX_ENV": "test",
                    "JUKEBOX_OPERATOR_STATE_PATH": str(Path(temp_dir) / "state.json"),
                }
            )

            with (
                patch("jukebox.runtime.CommandSystemHelpers", return_value=helper),
                patch("jukebox.runtime._build_playback_backend", return_value=playback),
            ):
                build_runtime(settings, io.StringIO(""))

        self.assertEqual(playback.probe_calls, 1)

    def test_build_runtime_raises_for_controller_auth_probe_failure(self) -> None:
        helper = _FakeSystemHelpers()
        playback = _FakePlaybackBackend(
            probe_result=PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_api_auth_error",
                message="Spotify controller auth unavailable.",
            ),
            status=DependencyStatus(
                code="controller_auth_unavailable",
                ready=False,
                message="Spotify controller auth unavailable.",
                reason_code="spotify_api_auth_error",
                backend="spotify",
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = from_env(
                {
                    "JUKEBOX_ENV": "test",
                    "JUKEBOX_OPERATOR_STATE_PATH": str(Path(temp_dir) / "state.json"),
                }
            )

            with (
                patch("jukebox.runtime.CommandSystemHelpers", return_value=helper),
                patch("jukebox.runtime._build_playback_backend", return_value=playback),
            ):
                with self.assertRaisesRegex(StartupError, "Spotify controller auth unavailable."):
                    build_runtime(settings, io.StringIO(""))

    def test_build_runtime_allows_degraded_probe_status(self) -> None:
        helper = _FakeSystemHelpers()
        playback = _FakePlaybackBackend(
            probe_result=PlaybackResult(
                ok=False,
                backend="spotify",
                reason_code="spotify_rate_limited",
                message="Spotify rate limited playback requests; retry in 30s.",
            ),
            status=DependencyStatus(
                code="spotify_rate_limited",
                ready=False,
                message="Spotify rate limited playback requests; retry in 30s.",
                reason_code="spotify_rate_limited",
                backend="spotify",
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = from_env(
                {
                    "JUKEBOX_ENV": "test",
                    "JUKEBOX_OPERATOR_STATE_PATH": str(Path(temp_dir) / "state.json"),
                }
            )

            with (
                patch("jukebox.runtime.CommandSystemHelpers", return_value=helper),
                patch("jukebox.runtime._build_playback_backend", return_value=playback),
            ):
                runtime = build_runtime(settings, io.StringIO(""))

            operator_server = next(
                service for service in runtime.services if isinstance(service, OperatorHttpServer)
            )
            response = operator_server.handle_request("GET", "/status.json")
            payload = response.json_body
            assert payload is not None
            runtime_payload = payload["runtime"]
            assert isinstance(runtime_payload, dict)
            playback_payload = runtime_payload["playback"]
            assert isinstance(playback_payload, dict)
            self.assertEqual(playback_payload["code"], "spotify_rate_limited")


class _FakeSystemHelpers:
    def __init__(self, *, auth_status_payload: dict[str, object] | None = None) -> None:
        self.auth_status_payload = auth_status_payload or {
            "state": "failed",
            "message": "auth not started",
        }

    def status(self) -> dict[str, bool]:
        return {
            "has_client_config": True,
            "client_connected": True,
            "ap_active": False,
        }

    def start_setup_ap(self) -> tuple[bool, str]:
        return True, "setup ap started"

    def apply_wifi(self, ssid: str, passphrase: str) -> str:
        del ssid, passphrase
        return "saved"

    def start_auth(self) -> dict[str, object]:
        return {"state": "pending"}

    def auth_status(self) -> dict[str, object]:
        return dict(self.auth_status_payload)

    def reset_wifi(self) -> tuple[bool, str]:
        return True, "wifi reset"

    def request_shutdown(self, *, reason: str) -> tuple[bool, str]:
        return True, f"shutdown requested: {reason}"


class _FakePlaybackBackend:
    def __init__(
        self,
        *,
        probe_result: PlaybackResult | None = None,
        status: DependencyStatus | None = None,
    ) -> None:
        self.probe_calls = 0
        self._probe_result = probe_result or PlaybackResult(
            ok=True,
            backend="stub",
            message="ready",
        )
        self._status = status or DependencyStatus(
            code="ready",
            ready=True,
            message="waiting for scan input",
            backend="stub",
        )

    def probe(self) -> PlaybackResult:
        self.probe_calls += 1
        return self._probe_result

    def status(self) -> DependencyStatus:
        return self._status

    def dispatch(self, request):  # type: ignore[no-untyped-def]
        del request
        return PlaybackResult(ok=True, backend="stub", message="played")

    def enqueue(self, request):  # type: ignore[no-untyped-def]
        del request
        return PlaybackResult(ok=True, backend="stub", message="queued")

    def stop(self) -> PlaybackResult:
        return PlaybackResult(ok=True, backend="stub", message="stopped")

    def skip_next(self) -> PlaybackResult:
        return PlaybackResult(ok=True, backend="stub", message="skipped")

    def set_volume_percent(self, percent: int) -> PlaybackResult:
        del percent
        return PlaybackResult(ok=True, backend="stub", message="volume set")

    def player_active(self) -> bool | None:
        return False

    def current_player_active(self) -> bool | None:
        return False
