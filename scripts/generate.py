#!/usr/bin/env python3.13

import argparse
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ModuleNotFoundError:
    print(
        "Error: Pillow is required. Install it with `python3.13 -m pip install Pillow`.",
        file=sys.stderr,
    )
    raise SystemExit(1)


CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 756
PADDING = 40
ARTWORK_HEIGHT_RATIO = 0.55
ARTIST_FONT_SIZE = 48
TITLE_FONT_SIZE = 42
MIN_FONT_SIZE = 20
TEXT_LINE_GAP = 65
TEXT_TOP_GAP = 20

try:
    RESAMPLING = Image.Resampling
except AttributeError:
    class _Resampling:
        NEAREST = Image.NEAREST
        LANCZOS = Image.LANCZOS

    RESAMPLING = _Resampling()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a music card PNG from a QR image, artwork, artist, and title."
    )
    parser.add_argument("--qr", required=True, help="Path to the QR code image.")
    parser.add_argument("--artwork", required=True, help="Path to the artwork image.")
    parser.add_argument("--artist", required=True, help="Artist name.")
    parser.add_argument("--title", required=True, help="Track title.")
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory for the generated PNG. Defaults to the current directory.",
    )
    return parser.parse_args()


def sanitize_filename(value: str) -> str:
    sanitized = re.sub(r'[:/\\\x00-\x1f]+', "-", value).strip()
    sanitized = re.sub(r"\s+", " ", sanitized)
    sanitized = sanitized.rstrip(". ")
    return sanitized or "card"


def resolve_input_path(path_str: str, label: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path


def open_rgb_image(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGB")


def center_crop_resize(image: Image.Image, target_width: int, target_height: int) -> Image.Image:
    image_ratio = image.width / image.height
    target_ratio = target_width / target_height

    if image_ratio > target_ratio:
        resized_width = int(round(target_height * image_ratio))
        resized = image.resize((resized_width, target_height), RESAMPLING.LANCZOS)
        crop_left = (resized_width - target_width) // 2
        return resized.crop((crop_left, 0, crop_left + target_width, target_height))

    resized_height = int(round(target_width / image_ratio))
    resized = image.resize((target_width, resized_height), RESAMPLING.LANCZOS)
    crop_top = (resized_height - target_height) // 2
    return resized.crop((0, crop_top, target_width, crop_top + target_height))


def candidate_font_paths() -> list[Path]:
    return [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ]


def load_font(preferred_size: int, bold: bool) -> ImageFont.ImageFont:
    ordered_candidates = []
    for path in candidate_font_paths():
        is_bold_path = "Bold" in path.name
        if is_bold_path == bold:
            ordered_candidates.append(path)
    for path in ordered_candidates:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), preferred_size)
            except OSError:
                continue
    return ImageFont.load_default()


def fit_text_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    initial_size: int,
    bold: bool,
) -> ImageFont.ImageFont:
    base_font = load_font(initial_size, bold)
    if not isinstance(base_font, ImageFont.FreeTypeFont):
        return base_font

    font_path = Path(base_font.path)
    size = initial_size
    while size >= MIN_FONT_SIZE:
        font = ImageFont.truetype(str(font_path), size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(str(font_path), MIN_FONT_SIZE)


def render_card(qr: Image.Image, artwork: Image.Image, artist: str, title: str) -> Image.Image:
    card = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "black")
    draw = ImageDraw.Draw(card)

    qr_size = CANVAS_HEIGHT - (2 * PADDING)
    qr_resized = qr.resize((qr_size, qr_size), RESAMPLING.NEAREST)
    card.paste(qr_resized, (PADDING, PADDING))

    artwork_width = CANVAS_WIDTH - qr_size - (3 * PADDING)
    artwork_height = int(CANVAS_HEIGHT * ARTWORK_HEIGHT_RATIO)
    artwork_final = center_crop_resize(artwork, artwork_width, artwork_height)

    artwork_x = qr_size + (2 * PADDING)
    artwork_y = PADDING
    card.paste(artwork_final, (artwork_x, artwork_y))

    text_x = artwork_x
    text_y = artwork_y + artwork_height + TEXT_TOP_GAP
    text_width = artwork_width

    artist_font = fit_text_font(draw, artist, text_width, ARTIST_FONT_SIZE, bold=True)
    title_font = fit_text_font(draw, title, text_width, TITLE_FONT_SIZE, bold=False)

    draw.text((text_x, text_y), artist, fill="white", font=artist_font)
    draw.text((text_x, text_y + TEXT_LINE_GAP), title, fill="white", font=title_font)

    return card


def main() -> int:
    args = parse_args()

    try:
        qr_path = resolve_input_path(args.qr, "QR image")
        artwork_path = resolve_input_path(args.artwork, "Artwork image")
        output_dir = Path(args.output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)

        qr_image = open_rgb_image(qr_path)
        artwork_image = open_rgb_image(artwork_path)

        card = render_card(qr_image, artwork_image, args.artist, args.title)
        output_name = f"{sanitize_filename(args.artist)} - {sanitize_filename(args.title)}.png"
        output_path = output_dir / output_name
        card.save(output_path)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
