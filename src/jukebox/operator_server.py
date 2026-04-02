"""Lightweight operator HTTP server."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from .feedback_state import FeedbackSnapshot

FeedbackSnapshotProvider = Callable[[], FeedbackSnapshot]
RuntimeStatusProvider = Callable[[], dict[str, object]]
WifiSubmitter = Callable[[str, str], str]
AuthStarter = Callable[[], dict[str, object]]


@dataclass(frozen=True)
class OperatorResponse:
    """A rendered operator HTTP response."""

    status_code: int
    content_type: str
    text_body: str | None = None
    json_body: dict[str, object] | None = None


class OperatorHttpServer:
    """Serve minimal maintenance HTML and JSON routes."""

    def __init__(
        self,
        *,
        bind: str,
        port: int,
        feedback_snapshot: FeedbackSnapshotProvider,
        runtime_status: RuntimeStatusProvider,
        submit_wifi: WifiSubmitter,
        start_auth: AuthStarter,
    ) -> None:
        self._bind = bind
        self._port = port
        self._feedback_snapshot = feedback_snapshot
        self._runtime_status = runtime_status
        self._submit_wifi = submit_wifi
        self._start_auth = start_auth
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        """Return the bound port after startup."""

        return self._port

    def start(self) -> None:
        """Start the HTTP server in a background thread."""

        if self._server is not None:
            return

        server = ThreadingHTTPServer((self._bind, self._port), self._handler_class())
        self._server = server
        self._port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True, name="jukebox-http")
        self._thread = thread
        thread.start()

    def stop(self) -> None:
        """Stop the HTTP server and join its thread."""

        server = self._server
        self._server = None
        if server is not None:
            server.shutdown()
            server.server_close()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=1.0)

    def handle_request(
        self,
        method: str,
        path: str,
        *,
        body: str = "",
    ) -> OperatorResponse:
        """Handle one request without binding a socket."""

        if method == "GET":
            if path == "/status.json":
                return OperatorResponse(
                    status_code=200,
                    content_type="application/json",
                    json_body={
                        "feedback": asdict(self._feedback_snapshot()),
                        "runtime": self._runtime_status(),
                    },
                )
            if path == "/wifi":
                return OperatorResponse(
                    status_code=200,
                    content_type="text/plain; charset=utf-8",
                    text_body="wifi setup",
                )
            if path == "/auth":
                return OperatorResponse(
                    status_code=200,
                    content_type="text/plain; charset=utf-8",
                    text_body="auth setup",
                )
            return OperatorResponse(
                status_code=200,
                content_type="text/plain; charset=utf-8",
                text_body="jukebox operator",
            )

        if method == "POST" and path == "/wifi":
            parsed = parse_qs(body, keep_blank_values=True)
            return OperatorResponse(
                status_code=200,
                content_type="text/plain; charset=utf-8",
                text_body=self._submit_wifi(
                    parsed.get("ssid", [""])[0],
                    parsed.get("passphrase", [""])[0],
                ),
            )
        if method == "POST" and path == "/auth/start":
            return OperatorResponse(
                status_code=200,
                content_type="application/json",
                json_body=self._start_auth(),
            )
        return OperatorResponse(
            status_code=404,
            content_type="text/plain; charset=utf-8",
            text_body="not found",
        )

    def _handler_class(self) -> type[BaseHTTPRequestHandler]:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                self._write_response(parent.handle_request("GET", self.path))

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8")
                self._write_response(parent.handle_request("POST", self.path, body=body))

            def log_message(self, format: str, *args: object) -> None:  # noqa: A003
                del format, args

            def _write_response(self, response: OperatorResponse) -> None:
                if response.json_body is not None:
                    body = json.dumps(response.json_body).encode("utf-8")
                else:
                    body = (response.text_body or "").encode("utf-8")
                self.send_response(response.status_code)
                self.send_header("Content-Type", response.content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return Handler
