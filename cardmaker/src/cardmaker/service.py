"""Application use cases for discovery, resolution, and verified rendering."""

from __future__ import annotations

import logging
import re
from io import BytesIO
from typing import Protocol

from PIL import Image

from cardmaker.errors import CardMakerError
from cardmaker.models import (
    ArtworkReference,
    CardDraft,
    CatalogItem,
    RenderedCard,
    SpotifyReference,
)
from cardmaker.references import InvalidSpotifyReference, SpotifyReferenceParser

MAX_SEARCH_QUERY_LENGTH = 200
_UNSAFE_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]+')
_WHITESPACE = re.compile(r"\s+")

logger = logging.getLogger(__name__)


class Catalog(Protocol):
    def search(self, query: str) -> tuple[CatalogItem, ...]: ...

    def resolve(self, reference: SpotifyReference) -> CatalogItem: ...


class ArtworkFetcher(Protocol):
    def fetch(self, reference: ArtworkReference) -> Image.Image: ...


class QrEncoder(Protocol):
    def encode(self, uri: str) -> Image.Image: ...


class QrVerifier(Protocol):
    def decode(self, image: Image.Image) -> str: ...


class CardRenderer(Protocol):
    def render(self, draft: CardDraft, qr_image: Image.Image) -> Image.Image: ...


class CardMakerService:
    """Coordinate Card Maker use cases without exposing HTTP concerns."""

    def __init__(
        self,
        *,
        catalog: Catalog,
        artwork_fetcher: ArtworkFetcher,
        qr_encoder: QrEncoder,
        qr_verifier: QrVerifier,
        renderer: CardRenderer,
        reference_parser: SpotifyReferenceParser | None = None,
    ) -> None:
        self._catalog = catalog
        self._artwork_fetcher = artwork_fetcher
        self._qr_encoder = qr_encoder
        self._qr_verifier = qr_verifier
        self._renderer = renderer
        self._reference_parser = reference_parser or SpotifyReferenceParser()

    def search(self, query: str) -> tuple[CatalogItem, ...]:
        """Validate and run one explicit catalog search."""

        normalized_query = query.strip()
        if not normalized_query:
            raise CardMakerError("invalid_query", "Enter a Spotify search term.")
        if len(normalized_query) > MAX_SEARCH_QUERY_LENGTH:
            raise CardMakerError(
                "invalid_query",
                f"Search terms must be at most {MAX_SEARCH_QUERY_LENGTH} characters.",
            )
        items = self._catalog.search(normalized_query)
        logger.info("catalog_search_succeeded result_count=%d", len(items))
        return items

    def resolve(self, raw_reference: str) -> CatalogItem:
        """Normalize a pasted Spotify reference and resolve fresh metadata."""

        reference = self._parse_reference(raw_reference)
        item = self._catalog.resolve(reference)
        logger.info("reference_resolved content_type=%s", reference.kind)
        return item

    def render(self, raw_reference: str) -> RenderedCard:
        """Resolve, render, independently verify, and serialize one in-memory card."""

        reference = self._parse_reference(raw_reference)
        item = self._catalog.resolve(reference)
        if item.reference != reference:
            raise CardMakerError(
                "spotify_unavailable", "Spotify returned metadata for a different item."
            )
        if item.artwork is None:
            raise CardMakerError(
                "artwork_unavailable",
                "This Spotify item has no usable artwork; other cover sources "
                "are not in the spike.",
            )

        artwork = self._artwork_fetcher.fetch(item.artwork)
        draft = CardDraft(item=item, artwork=artwork)
        qr_image = self._qr_encoder.encode(reference.uri)
        card_image = self._renderer.render(draft, qr_image)
        decoded = self._qr_verifier.decode(card_image)
        if decoded != reference.uri:
            raise CardMakerError(
                "qr_verification_failed",
                "The composed card QR did not decode to the selected Spotify item.",
            )

        output = BytesIO()
        card_image.save(output, format="PNG", dpi=(72, 72), compress_level=9)
        logger.info(
            "card_render_succeeded content_type=%s width=%d height=%d",
            reference.kind,
            card_image.width,
            card_image.height,
        )
        return RenderedCard(
            png_bytes=output.getvalue(),
            normalized_uri=reference.uri,
            filename=safe_filename(item.primary_label, item.secondary_label),
            width=card_image.width,
            height=card_image.height,
        )

    def _parse_reference(self, raw_reference: str) -> SpotifyReference:
        try:
            return self._reference_parser.parse(raw_reference)
        except InvalidSpotifyReference as exc:
            logger.info("reference_rejected error_code=invalid_reference")
            raise CardMakerError("invalid_reference", str(exc)) from None


def safe_filename(primary_label: str, secondary_label: str | None) -> str:
    """Derive a portable PNG name from trusted Spotify labels."""

    parts = [_safe_filename_part(primary_label)]
    if secondary_label is not None:
        parts.append(_safe_filename_part(secondary_label))
    stem = " - ".join(part for part in parts if part)
    return f"{stem or 'card'}.png"


def _safe_filename_part(value: str) -> str:
    value = _UNSAFE_FILENAME.sub("-", value)
    value = _WHITESPACE.sub(" ", value).strip()
    return value.rstrip(". ")
