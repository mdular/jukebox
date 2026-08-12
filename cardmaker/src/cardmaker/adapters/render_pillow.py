"""Deterministic Pillow renderer for the locked 1200 x 756 music card."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from cardmaker.models import CardDraft


@dataclass(frozen=True, slots=True)
class CardGeometry:
    """Frozen geometry recovered from the checked-in card masters."""

    canvas_width: int = 1200
    canvas_height: int = 756
    margin: int = 40
    qr_x: int = 40
    qr_y: int = 40
    qr_panel_size: int = 676
    content_x: int = 756
    content_width: int = 404
    artwork_y: int = 40
    artwork_height: int = 453
    text_top_gap: int = 20
    text_line_gap: int = 65
    primary_font_size: int = 48
    secondary_font_size: int = 42
    minimum_font_size: int = 20


@dataclass(frozen=True, slots=True)
class FittedText:
    text: str
    font_size: int
    measured_width: int


class PillowCardRenderer:
    """Compose QR, unmodified-aspect Spotify art, and deterministic labels."""

    font_names = ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf")

    def __init__(self, geometry: CardGeometry | None = None) -> None:
        self.geometry = CardGeometry() if geometry is None else geometry
        font_root = files("cardmaker") / "assets" / "fonts"
        with as_file(font_root / self.font_names[0]) as path:
            self.bold_font_path = Path(path)
        with as_file(font_root / self.font_names[1]) as path:
            self.regular_font_path = Path(path)

    def render(self, draft: CardDraft, qr_image: Image.Image) -> Image.Image:
        geometry = self.geometry
        if qr_image.size != (geometry.qr_panel_size, geometry.qr_panel_size):
            raise ValueError("The QR encoder must return the final 676 x 676 panel.")

        card = Image.new(
            "RGB", (geometry.canvas_width, geometry.canvas_height), (0, 0, 0)
        )
        card.paste(qr_image.convert("RGB"), (geometry.qr_x, geometry.qr_y))

        artwork = draft.artwork.convert("RGB")
        contained = ImageOps.contain(
            artwork,
            (geometry.content_width, geometry.artwork_height),
            method=Image.Resampling.LANCZOS,
        )
        artwork_x = geometry.content_x + ((geometry.content_width - contained.width) // 2)
        card.paste(contained, (artwork_x, geometry.artwork_y))

        draw = ImageDraw.Draw(card)
        primary = fit_text(
            draft.item.primary_label,
            font_path=self.bold_font_path,
            max_width=geometry.content_width,
            initial_size=geometry.primary_font_size,
            minimum_size=geometry.minimum_font_size,
        )
        primary_font = ImageFont.truetype(str(self.bold_font_path), primary.font_size)
        text_y = geometry.artwork_y + geometry.artwork_height + geometry.text_top_gap
        draw.text(
            (geometry.content_x, text_y), primary.text, font=primary_font, fill=(255, 255, 255)
        )

        if draft.item.secondary_label is not None:
            secondary = fit_text(
                draft.item.secondary_label,
                font_path=self.regular_font_path,
                max_width=geometry.content_width,
                initial_size=geometry.secondary_font_size,
                minimum_size=geometry.minimum_font_size,
            )
            secondary_font = ImageFont.truetype(
                str(self.regular_font_path), secondary.font_size
            )
            draw.text(
                (geometry.content_x, text_y + geometry.text_line_gap),
                secondary.text,
                font=secondary_font,
                fill=(255, 255, 255),
            )
        return card


def fit_text(
    text: str,
    *,
    font_path: Path,
    max_width: int,
    initial_size: int,
    minimum_size: int,
) -> FittedText:
    """Shrink in two-pixel steps, then ellipsize at the minimum size."""

    size = initial_size
    while size >= minimum_size:
        font = ImageFont.truetype(str(font_path), size)
        width = _text_width(text, font)
        if width <= max_width:
            return FittedText(text=text, font_size=size, measured_width=width)
        size -= 2

    font = ImageFont.truetype(str(font_path), minimum_size)
    ellipsis = "…"
    candidate = text.rstrip()
    while candidate and _text_width(candidate + ellipsis, font) > max_width:
        candidate = candidate[:-1].rstrip()
    fitted = (candidate + ellipsis) if candidate else ellipsis
    return FittedText(
        text=fitted,
        font_size=minimum_size,
        measured_width=_text_width(fitted, font),
    )


def _text_width(text: str, font: ImageFont.FreeTypeFont) -> int:
    left, _, right, _ = font.getbbox(text)
    return int(right - left)
