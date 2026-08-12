# Card Maker spike validation

Date: 2026-08-12

Status: automated implementation complete; live Spotify, physical scanner, print, and
lamination validation remain incomplete. The spike does not yet meet its full exit
criteria because those checks require credentials and hardware that were not available
during implementation.

## Reproduction

Install and run the isolated distribution:

```sh
cd cardmaker
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
export CARDMAKER_SPOTIFY_CLIENT_ID='...'
export CARDMAKER_SPOTIFY_CLIENT_SECRET='...'
export CARDMAKER_SPOTIFY_MARKET='DE'
.venv/bin/python -m cardmaker
```

The development server defaults to `http://127.0.0.1:8081/`. Optional process
variables are `CARDMAKER_HTTP_BIND`, `CARDMAKER_HTTP_PORT`, and
`CARDMAKER_LOG_LEVEL`. The app does not read a repository secrets file.

Automated checks:

```sh
cd cardmaker
.venv/bin/ruff check src tests tools
.venv/bin/mypy
.venv/bin/pytest
.venv/bin/python tools/inspect_golden_masters.py
```

## Golden-master measurements

All four masters are RGB PNGs at 1200 x 756. Their non-black content begins at
`(40, 40)`, the QR panel occupies inclusive bounds `(40, 40)` through `(715, 715)`,
and the content column begins at `x = 756`.

| Master | Visible artwork bounds | Text bounds | QR dark bounds | Decoded URI |
| --- | --- | --- | --- | --- |
| `laternenlauf_card.png` | `(756,40)`–`(1159,454)` | `(760,494)`–`(1132,534)` | `(78,76)`–`(679,679)` | `spotify:track:2F9VY2gYvXz47Xbh9Ranea` |
| `lichterkinder_qr_card_with_art.png` | `(756,40)`–`(1159,492)` | `(760,522)`–`(1117,625)` | `(80,80)`–`(671,673)` | `spotify:track:3wECJLFkS6cGvdyVOmGFme` |
| `nin_qr_card.png` | `(774,56)`–`(1144,401)` | `(756,494)`–`(1191,593)` | `(78,78)`–`(673,673)` | `spotify:track:06USX1htQD4LgOgX4FF0ix` |
| `willy_astor_qr_card.png` | `(756,40)`–`(1159,492)` | `(757,522)`–`(1051,616)` | `(78,80)`–`(677,677)` | `spotify:track:4m6MeQUIEcnMWEDDQDQc7j` |

`zxing-cpp` reports error correction `H` for every master. A two-module quiet zone
most closely recovers their visible symbol size. For a representative version-5
spike QR, the 37-module symbol plus quiet zone uses a 16-pixel integer module scale,
is centered in the 676-pixel panel, and has dark bounds `(82,82)`–`(673,673)` after
composition. No QR raster resize occurs.

The master PNG byte streams contain no `pHYs` chunk and Pillow reports no DPI
metadata. macOS `sips` presents them as 72 DPI by default. Spike output explicitly
writes 72 DPI, which Pillow reads back as approximately 72.009 DPI; physical print
size must still be measured rather than inferred from either value.

## Renderer decisions and comparison

- The renderer packages DejaVu Sans 2.37 regular and bold under its included font
  license. This matches the old generator's first Linux font choice and avoids any
  host font search or fallback.
- Primary text starts at 48 pixels and secondary text at 42 pixels. Overflow shrinks
  in two-pixel steps to 20 pixels, then uses one line with an ellipsis.
- Artwork is contained in a 404 x 453 maximum area at `(756, 40)`. Its aspect ratio
  is preserved, and unused area remains black. This matches the full portrait-art
  height in the Lichterkinder and Willy Astor masters without reintroducing the old
  crop operation.
- The checked-in `tests/fixtures/approved-card.png` is the reviewed deterministic
  fixture. Its 1200 x 756 geometry, integer-grid QR, packaged-font text, and synthetic
  artwork placement are pixel-compared in tests.
- The master set is not internally identical: artwork heights and first text rows
  differ, the Nine Inch Nails secondary line exceeds the canonical right margin, and
  the Laternenlauf primary line is visibly larger than the two-line baseline. The
  spike keeps one deterministic 1200-pixel layout and the specified shrink/ellipsis
  shortcut rather than reproducing those per-card variations.
- The masters show lightly resampled panel-edge pixels from their earlier workflow.
  The spike uses a square, solid-white panel because no stable non-zero corner cutout
  can be recovered from those pixels. The QR itself is never antialiased.

## Automated evidence

- Reference tests cover track, album, and playlist URIs and URLs, locale removal,
  tracking removal, rejected hosts/types/path content, and the jukebox parser
  contract.
- Spotify adapter tests cover three-type mapping, multiple-artist order, Unicode,
  largest image choice, bounded search, token reuse/refresh, 401/403/404/429,
  `Retry-After`, network failure, malformed JSON, and empty results.
- Artwork tests cover HTTPS-only requests, supported raster types, byte bounds,
  invalid images, RGB conversion, and response closure.
- Real Segno encoding and independent zxing decoding run in tests for both the final
  panel and composed card. A mismatched decode prevents PNG return.
- Flask tests cover the page shell, health isolation, strict request shapes, search,
  resolve, inline render response, exact blob reuse contract, JSON errors, no-store
  headers, and non-disclosure of unexpected error details.
- No test or application route writes rendered cards, Spotify metadata, or artwork
  to a runtime cache or server output directory.

## Manual evidence still required

- [ ] Configure live Spotify credentials and record one selected track, album, and
  playlist with their full labels and normalized URIs.
- [ ] Record the independent decoder output for all three live examples.
- [ ] Save one live generated example of each supported type for review.
- [ ] Scan at least one full-resolution on-screen preview with the actual presentation
  scanner.
- [ ] Record the printer model, application, scale setting, paper, orientation, and
  measured physical output dimensions from the established workflow.
- [ ] Print and laminate one card, then scan it with the actual presentation scanner.
- [ ] Review Spotify attribution and link-back behavior against the applicable policy
  before any use beyond the private household spike.

Until those items are checked with real evidence, fixture-only progress must not be
reported as a successful spike exit or used to justify a large print run.
