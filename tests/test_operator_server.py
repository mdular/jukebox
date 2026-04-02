"""Tests for the operator HTTP server."""

from __future__ import annotations

import unittest

from jukebox.core.models import ControllerEvent
from jukebox.feedback_state import FeedbackStateTracker
from jukebox.operator_server import OperatorHttpServer


class OperatorHttpServerTests(unittest.TestCase):
    def test_status_json_exposes_feedback_snapshot(self) -> None:
        tracker = FeedbackStateTracker()
        tracker.handle(ControllerEvent(code="ready", message="waiting for scan input"))
        auth_calls: list[str] = []
        wifi_calls: list[tuple[str, str]] = []

        def start_auth() -> dict[str, object]:
            auth_calls.append("auth")
            return {"state": "pending"}

        server = OperatorHttpServer(
            bind="127.0.0.1",
            port=0,
            feedback_snapshot=tracker.snapshot,
            runtime_status=lambda: {
                "playback_mode": "replace",
                "setup_required": False,
                "auth_required": False,
            },
            submit_wifi=lambda ssid, passphrase: _record_wifi(wifi_calls, ssid, passphrase),
            start_auth=start_auth,
        )

        response = server.handle_request("GET", "/status.json")

        payload = response.json_body
        assert payload is not None
        feedback = payload["feedback"]
        runtime = payload["runtime"]
        assert isinstance(feedback, dict)
        assert isinstance(runtime, dict)
        self.assertEqual(feedback["display_state"], "ready")
        self.assertEqual(runtime["playback_mode"], "replace")
        self.assertEqual(auth_calls, [])
        self.assertEqual(wifi_calls, [])

    def test_wifi_and_auth_routes_call_callbacks(self) -> None:
        tracker = FeedbackStateTracker()
        auth_calls: list[str] = []
        wifi_calls: list[tuple[str, str]] = []

        def start_auth() -> dict[str, object]:
            auth_calls.append("auth")
            return {"state": "pending"}

        server = OperatorHttpServer(
            bind="127.0.0.1",
            port=0,
            feedback_snapshot=tracker.snapshot,
            runtime_status=lambda: {},
            submit_wifi=lambda ssid, passphrase: _record_wifi(wifi_calls, ssid, passphrase),
            start_auth=start_auth,
        )

        wifi_response = server.handle_request(
            "POST",
            "/wifi",
            body="ssid=kids-room&passphrase=secret-pass",
        )
        auth_response = server.handle_request("POST", "/auth/start")

        assert wifi_response.text_body is not None
        assert auth_response.json_body is not None
        self.assertIn("saved", wifi_response.text_body)
        self.assertEqual(auth_response.json_body["state"], "pending")
        self.assertEqual(wifi_calls, [("kids-room", "secret-pass")])
        self.assertEqual(auth_calls, ["auth"])


def _record_wifi(calls: list[tuple[str, str]], ssid: str, passphrase: str) -> str:
    calls.append((ssid, passphrase))
    return "saved"
