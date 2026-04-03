#!/usr/bin/env python3
"""Generate SVG QR codes for the EPIC-4 validation payload set."""

from __future__ import annotations

from pathlib import Path

VERSION = 3
SIZE = 21 + (VERSION - 1) * 4
DATA_CODEWORDS = 55
ECC_CODEWORDS = 15
FINDER_POSITIONS = ((0, 0), (SIZE - 7, 0), (0, SIZE - 7))
ALIGNMENT_CENTER = 22
BORDER = 4
MASK = 0
EC_LEVEL_BITS = 0b01  # L

PAYLOADS = (
    ("control-smoke-track", "spotify:track:6rqhFgbbKwnb9MLmUQDhG6"),
    ("control-fallback-album", "spotify:album:1ATL5GLyefJaxhQzSPVrLX"),
    ("control-fallback-playlist", "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"),
    ("control-playback-stop", "jukebox:playback:stop"),
    ("control-playback-next", "jukebox:playback:next"),
    ("control-mode-replace", "jukebox:mode:replace"),
    ("control-mode-queue", "jukebox:mode:queue"),
    ("control-volume-low", "jukebox:volume:low"),
    ("control-volume-medium", "jukebox:volume:medium"),
    ("control-volume-high", "jukebox:volume:high"),
    ("control-setup-wifi-reset", "jukebox:setup:wifi-reset"),
    ("control-setup-receiver-reauth", "jukebox:setup:receiver-reauth"),
    ("control-system-shutdown", "jukebox:system:shutdown"),
)


def main() -> None:
    output_dir = Path("docs/qr codes/control")
    output_dir.mkdir(parents=True, exist_ok=True)

    for stem, payload in PAYLOADS:
        modules = build_qr_modules(payload)
        write_svg(output_dir / f"{stem}.svg", payload, modules)


def build_qr_modules(payload: str) -> list[list[bool]]:
    data = encode_payload(payload)
    ecc = reed_solomon_remainder(data, ECC_CODEWORDS)
    codewords = data + ecc
    bitstream = []
    for byte in codewords:
        for shift in range(7, -1, -1):
            bitstream.append(((byte >> shift) & 1) != 0)

    modules = [[False] * SIZE for _ in range(SIZE)]
    function = [[False] * SIZE for _ in range(SIZE)]

    draw_function_patterns(modules, function)
    draw_codewords(modules, function, bitstream)
    apply_mask(modules, function)
    draw_format_bits(modules, function)
    return modules


def encode_payload(payload: str) -> list[int]:
    data = payload.encode("utf-8")
    if len(data) > 53:
        raise ValueError(f"Payload too long for fixed QR version: {payload}")

    bits: list[int] = []
    append_bits(bits, 0b0100, 4)
    append_bits(bits, len(data), 8)
    for byte in data:
        append_bits(bits, byte, 8)

    capacity = DATA_CODEWORDS * 8
    terminator = min(4, capacity - len(bits))
    append_bits(bits, 0, terminator)
    while len(bits) % 8 != 0:
        bits.append(0)

    codewords = []
    for index in range(0, len(bits), 8):
        value = 0
        for bit in bits[index : index + 8]:
            value = (value << 1) | bit
        codewords.append(value)

    pad_bytes = (0xEC, 0x11)
    pad_index = 0
    while len(codewords) < DATA_CODEWORDS:
        codewords.append(pad_bytes[pad_index % 2])
        pad_index += 1
    return codewords


def append_bits(bits: list[int], value: int, width: int) -> None:
    for shift in range(width - 1, -1, -1):
        bits.append((value >> shift) & 1)


def reed_solomon_remainder(data: list[int], degree: int) -> list[int]:
    generator = [1]
    for index in range(degree):
        generator = poly_mul(generator, [1, gf_pow(2, index)])

    remainder = [0] * degree
    for byte in data:
        factor = byte ^ remainder[0]
        remainder = remainder[1:] + [0]
        for index, coefficient in enumerate(generator[1:]):
            remainder[index] ^= gf_mul(coefficient, factor)
    return remainder


def poly_mul(left: list[int], right: list[int]) -> list[int]:
    result = [0] * (len(left) + len(right) - 1)
    for i, left_value in enumerate(left):
        for j, right_value in enumerate(right):
            result[i + j] ^= gf_mul(left_value, right_value)
    return result


def gf_mul(left: int, right: int) -> int:
    result = 0
    while right:
        if right & 1:
            result ^= left
        left <<= 1
        if left & 0x100:
            left ^= 0x11D
        right >>= 1
    return result


def gf_pow(value: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result = gf_mul(result, value)
    return result


def draw_function_patterns(modules: list[list[bool]], function: list[list[bool]]) -> None:
    for x, y in FINDER_POSITIONS:
        draw_finder(modules, function, x, y)

    draw_alignment(modules, function, ALIGNMENT_CENTER, ALIGNMENT_CENTER)

    for index in range(8, SIZE - 8):
        value = index % 2 == 0
        set_function(modules, function, index, 6, value)
        set_function(modules, function, 6, index, value)

    for index in range(9):
        if index != 6:
            set_function(modules, function, 8, index, False)
            set_function(modules, function, index, 8, False)

    for index in range(8):
        set_function(modules, function, SIZE - 1 - index, 8, False)
        set_function(modules, function, 8, SIZE - 1 - index, False)

    set_function(modules, function, 8, SIZE - 8, True)


def draw_finder(
    modules: list[list[bool]],
    function: list[list[bool]],
    x0: int,
    y0: int,
) -> None:
    for dy in range(-1, 8):
        for dx in range(-1, 8):
            x = x0 + dx
            y = y0 + dy
            if not (0 <= x < SIZE and 0 <= y < SIZE):
                continue
            value = (
                0 <= dx <= 6
                and 0 <= dy <= 6
                and (
                    dx in {0, 6}
                    or dy in {0, 6}
                    or (2 <= dx <= 4 and 2 <= dy <= 4)
                )
            )
            set_function(modules, function, x, y, value)


def draw_alignment(
    modules: list[list[bool]],
    function: list[list[bool]],
    x0: int,
    y0: int,
) -> None:
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            value = max(abs(dx), abs(dy)) != 1
            set_function(modules, function, x0 + dx, y0 + dy, value)


def set_function(
    modules: list[list[bool]],
    function: list[list[bool]],
    x: int,
    y: int,
    value: bool,
) -> None:
    modules[y][x] = value
    function[y][x] = True


def draw_codewords(
    modules: list[list[bool]],
    function: list[list[bool]],
    bits: list[bool],
) -> None:
    bit_index = 0
    upward = True
    x = SIZE - 1
    while x > 0:
        if x == 6:
            x -= 1
        y_values = range(SIZE - 1, -1, -1) if upward else range(SIZE)
        for y in y_values:
            for dx in (0, -1):
                current_x = x + dx
                if function[y][current_x]:
                    continue
                modules[y][current_x] = bits[bit_index] if bit_index < len(bits) else False
                bit_index += 1
        upward = not upward
        x -= 2


def apply_mask(modules: list[list[bool]], function: list[list[bool]]) -> None:
    for y in range(SIZE):
        for x in range(SIZE):
            if function[y][x]:
                continue
            if (x + y) % 2 == 0:
                modules[y][x] = not modules[y][x]


def draw_format_bits(modules: list[list[bool]], function: list[list[bool]]) -> None:
    data = (EC_LEVEL_BITS << 3) | MASK
    remainder = data << 10
    for bit in range(14, 9, -1):
        if ((remainder >> bit) & 1) != 0:
            remainder ^= 0x537 << (bit - 10)
    bits = ((data << 10) | remainder) ^ 0x5412

    for index in range(6):
        set_function(modules, function, 8, index, get_bit(bits, index))
    set_function(modules, function, 8, 7, get_bit(bits, 6))
    set_function(modules, function, 8, 8, get_bit(bits, 7))
    set_function(modules, function, 7, 8, get_bit(bits, 8))
    for index in range(9, 15):
        set_function(modules, function, 14 - index, 8, get_bit(bits, index))

    for index in range(8):
        set_function(modules, function, SIZE - 1 - index, 8, get_bit(bits, index))
    for index in range(8, 15):
        set_function(modules, function, 8, SIZE - 15 + index, get_bit(bits, index))
    set_function(modules, function, 8, SIZE - 8, True)


def get_bit(value: int, index: int) -> bool:
    return ((value >> index) & 1) != 0


def write_svg(path: Path, payload: str, modules: list[list[bool]]) -> None:
    dimension = SIZE + BORDER * 2
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {dimension} {dimension}" '
            'shape-rendering="crispEdges">'
        ),
        f"  <title>{escape_xml(payload)}</title>",
        '  <rect width="100%" height="100%" fill="#ffffff"/>',
        '  <g fill="#000000">',
    ]
    for y, row in enumerate(modules):
        for x, value in enumerate(row):
            if value:
                lines.append(
                    f'    <rect x="{x + BORDER}" y="{y + BORDER}" width="1" height="1"/>'
                )
    lines.extend(["  </g>", "</svg>"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


if __name__ == "__main__":
    main()
