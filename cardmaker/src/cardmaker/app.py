"""Flask application factory and thin HTTP routes for Card Maker."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Protocol, cast

from flask import Flask, Response, jsonify, render_template, request, send_file
from werkzeug.exceptions import HTTPException

from cardmaker.adapters.artwork_http import ArtworkHttpFetcher
from cardmaker.adapters.qr_segno import SegnoQrEncoder
from cardmaker.adapters.qr_zxing import ZxingQrVerifier
from cardmaker.adapters.render_pillow import PillowCardRenderer
from cardmaker.adapters.spotify_catalog import SpotifyCatalog
from cardmaker.config import Settings
from cardmaker.errors import CardMakerError
from cardmaker.models import CatalogItem, RenderedCard
from cardmaker.service import CardMakerService

logger = logging.getLogger(__name__)

_ERROR_STATUS = {
    "invalid_request": 400,
    "invalid_query": 400,
    "invalid_reference": 400,
    "spotify_forbidden": 403,
    "spotify_not_found": 404,
    "spotify_rate_limited": 429,
    "artwork_unavailable": 422,
    "qr_verification_failed": 422,
    "spotify_auth_failed": 502,
    "spotify_unavailable": 503,
}


class AppService(Protocol):
    def search(self, query: str) -> tuple[CatalogItem, ...]: ...

    def resolve(self, raw_reference: str) -> CatalogItem: ...

    def render(self, raw_reference: str) -> RenderedCard: ...


def create_app(
    settings: Settings | None = None, *, service: AppService | None = None
) -> Flask:
    """Create the stable Card Maker WSGI application."""

    active_service = service
    if active_service is None:
        active_settings = Settings.from_environ() if settings is None else settings
        active_service = _build_service(active_settings)

    app = Flask(
        __name__,
        template_folder="web/templates",
        static_folder="web/static",
        static_url_path="/static",
    )

    @app.after_request
    def prevent_api_caching(response: Response) -> Response:
        if request.path == "/healthz" or request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/healthz")
    def health() -> Response:
        return jsonify(status="ok")

    @app.get("/api/search")
    def search() -> Response:
        items = active_service.search(request.args.get("q", ""))
        return jsonify(items=[_serialize_item(item) for item in items])

    @app.post("/api/resolve")
    def resolve() -> Response:
        raw_reference = _single_json_string("reference")
        return jsonify(item=_serialize_item(active_service.resolve(raw_reference)))

    @app.post("/api/render")
    def render() -> Response:
        raw_uri = _single_json_string("uri")
        rendered = active_service.render(raw_uri)
        response = send_file(
            BytesIO(rendered.png_bytes),
            mimetype="image/png",
            as_attachment=False,
            download_name=rendered.filename,
            max_age=0,
        )
        response.headers["X-Cardmaker-Spotify-URI"] = rendered.normalized_uri
        response.headers["X-Cardmaker-Width"] = str(rendered.width)
        response.headers["X-Cardmaker-Height"] = str(rendered.height)
        return response

    @app.errorhandler(CardMakerError)
    def expected_error(error: CardMakerError) -> tuple[Response, int]:
        logger.warning("cardmaker_request_failed error_code=%s", error.code)
        response = jsonify(code=error.code, message=error.message)
        if error.retry_after is not None:
            response.headers["Retry-After"] = str(error.retry_after)
        return response, _ERROR_STATUS.get(error.code, 400)

    @app.errorhandler(Exception)
    def unexpected_error(error: Exception) -> Response | tuple[Response, int]:
        if isinstance(error, HTTPException):
            if request.path.startswith("/api/"):
                return (
                    jsonify(
                        code="invalid_request",
                        message="That Card Maker API route or method is not available.",
                    ),
                    error.code or 500,
                )
            return cast(Response, error.get_response())
        logger.error(
            "cardmaker_request_failed error_code=internal_error exception_type=%s",
            type(error).__name__,
        )
        return (
            jsonify(
                code="internal_error",
                message="The Card Maker could not complete that request.",
            ),
            500,
        )

    return app


def _build_service(settings: Settings) -> CardMakerService:
    return CardMakerService(
        catalog=SpotifyCatalog(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            market=settings.spotify_market,
        ),
        artwork_fetcher=ArtworkHttpFetcher(),
        qr_encoder=SegnoQrEncoder(),
        qr_verifier=ZxingQrVerifier(),
        renderer=PillowCardRenderer(),
    )


def _single_json_string(field: str) -> str:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {field}:
        raise CardMakerError(
            "invalid_request", f"Request JSON must contain only the string field '{field}'."
        )
    value = payload.get(field)
    if not isinstance(value, str):
        raise CardMakerError(
            "invalid_request", f"Request JSON field '{field}' must be a string."
        )
    return value


def _serialize_item(item: CatalogItem) -> dict[str, object]:
    artwork: dict[str, object] | None = None
    if item.artwork is not None:
        artwork = {
            "url": item.artwork.url,
            "width": item.artwork.width,
            "height": item.artwork.height,
        }
    return {
        "kind": item.reference.kind,
        "spotify_id": item.reference.spotify_id,
        "uri": item.reference.uri,
        "external_url": item.external_url,
        "primary_label": item.primary_label,
        "secondary_label": item.secondary_label,
        "artwork": artwork,
    }
