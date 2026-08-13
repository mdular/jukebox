# Card Maker validation record

Started: 2026-08-12
Updated: 2026-08-13

Status: automated CM-1 implementation and the current immediate-preview browser flow
are validated. The prior live track artifact remains valid URI/decode evidence. Live
album and playlist, presentation-scanner, measured print, lamination, and final-scanner
evidence remain incomplete.

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
- CM-1 now bottom-aligns every marker in a 56 x 36 box at `(756, 680)`, immediately
  above the 40-pixel bottom margin. The album is a disc with hub, center hole, and
  tonal reflection wedge; playlist line lengths vary subtly; the track uses one
  enlarged dot-dash row. All use deterministic 4x supersampling for smoother edges.
- The checked-in `tests/fixtures/approved-card.png` is the reviewed CM-1 deterministic
  track fixture. Its 1200 x 756 geometry, integer-grid QR, packaged-font text,
  synthetic artwork placement, and track marker are pixel-compared in tests. The
  selected single-track-row fixture has SHA-256
  `e6cc62df6a7704a9ed328ad62d2714df52b8d81f1da590d2f98bce5d1dfaacf9`.
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
- Renderer and service tests cover the exact track, album, and playlist marker bounds,
  representative foreground/background pixels, bottom-left alignment, album reflection,
  playlist-without-secondary behavior, deterministic output, exact independent decode,
  and no server output file.
- Flask tests cover the page shell, health isolation, strict request shapes, search,
  resolve, attachment render response, exact response-byte reuse, JSON errors, no-store
  headers, and non-disclosure of unexpected error details. Browser-shell checks freeze
  one render fetch on selection, one Blob read, one programmatic download click that
  reuses the preview URL, response-integrity headers, abort handling, and object-URL
  cleanup.
- No test or application route writes rendered cards, Spotify metadata, or artwork
  to a runtime cache or server output directory.

## CM-1 candidate comparison and automated gate

The controlled track, album, and playlist candidates were rendered at full 1200 x 756
resolution and compared side by side with the prior synthetic fixture and all four
historical masters. The packaged fonts, 48/42-pixel starting sizes, label offsets,
404 x 453 contained-artwork region, QR panel, gap, and 1200-pixel canvas remained
unchanged. At full image size the three marker meanings were legible and subordinate
to the artwork, labels, and QR.

The refined candidate was regenerated through `tools/create_approved_fixture.py`
and deliberately replaced the approved fixture. The four historical golden PNGs
were not changed. Legibility after physical printing and lamination remains part
of the open release gate.

Automated gate on 2026-08-13:

- `ruff check src tests tools`: all checks passed.
- `mypy`: no issues in 24 source files.
- `pytest`: 97 passed.
- `node --check src/cardmaker/web/static/app.js`: JavaScript syntax check passed.
- `tools/inspect_golden_masters.py`: all four historical masters remained readable at
  1200 x 756 RGB with their previously recorded geometry and exact decoded URIs.

The Flask response contract and browser shell are automated. Playwright verifies the
current selection, preview, and download interaction below.

## CM-1 Playwright browser evidence — 2026-08-13 (before single-track row)

Playwright opened `http://127.0.0.1:8081/` against the deterministic local service
and approved CM-1 fixture. Resolving
`spotify:track:2takcwOaAZWiXQijPHIx7B` made one successful `POST /api/render`
request and automatically displayed the verified preview.

- Preview natural size: 1200 x 756.
- Responsive layout measurements:
  - 1280-pixel desktop: two 513-pixel columns; preview and metadata share the same
    top edge.
  - 768-pixel tablet: two 331-pixel columns; preview and metadata remain adjacent.
  - 500-pixel mobile: one 418-pixel column; metadata begins 24 pixels below the
    preview.
- Preview source: retained browser Blob URL.
- DOM order remains preview first; encoded URI and Spotify credit precede the
  `Download PNG` and `Make another` actions inside the metadata panel.
- Download state: enabled only after the preview status reported
  `Preview verified and ready to download.`
- Download result: `Lichterkinder - Körperteil Blues.png`, RGB 1200 x 756.
- Download SHA-256: `0e707ddd521bfe4b8e209e0389551d466305d3d654cec9bfdc3207d67cb7372b`,
  which matched the approved fixture before its single-track-row replacement.
- Network after download: still one `POST /api/render`; no second render occurred.
- Browser status after download: `Download started. Review the PNG before printing.`
- Console: only the known non-blocking `/favicon.ico` 404; no application error.
- Desktop screenshot: `.playwright-mcp/page-2026-08-13T10-03-57-920Z.png`.
- Mobile screenshot: `.playwright-mcp/page-2026-08-13T10-03-48-743Z.png`.

This deterministic browser run validates the retained UI and Blob-reuse behavior. It
predates the single-track-row marker and does not validate the current approved
fixture, live Spotify type coverage, or physical scanner evidence.

## Prior CM-1 Playwright browser evidence — 2026-08-13

This evidence predates the immediate-preview and refined bottom-left-symbol
iteration. It remains valid for the retained live track file and its decoded URI,
but it does not validate the current review-screen interaction or symbol geometry.

Playwright navigated to `http://127.0.0.1:8081/` successfully. The shell title was
`Jukebox Card Maker`; `/`, `static/style.css`, and `static/app.js` each returned 200.
The only browser-console error was a 404 for `/favicon.ico`, which did not prevent
the card flow.

The direct resolution of `spotify:track:2takcwOaAZWiXQijPHIx7B` returned 200 and
presented the live Spotify labels shown below. One click on **Download PNG** produced
one `POST /api/render` request (200), initiated one download with no preview, and
showed the status `Download started. Review the PNG before printing.` The response was
an attachment with the recorded filename, `Content-Type: image/png`, `Cache-Control:
no-store`, `X-CardMaker-Width: 1200`, `X-CardMaker-Height: 756`, and the matching
`X-CardMaker-Spotify-Uri`. The retained artifact was RGB, 1200 x 756, and its
independent `zxing-cpp` decode was the exact normalized URI at error correction H.

This validates the local browser download path for one live track only. It does not
validate a live album or playlist, the presentation scanner, printing, or lamination.

## CM-1 live type evidence — partial

The track row below comes from the direct Playwright browser download, not fixture or
synthetic data. Album and playlist remain open until direct live downloads are
performed and retained.

| Type | Full primary label | Full secondary label | Normalized URI | Browser filename | Review-file location | Independent `zxing-cpp` output | Visible marker | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Track | Muse | Time is Running Out | `spotify:track:2takcwOaAZWiXQijPHIx7B` | `Muse - Time is Running Out.png` | `.playwright-mcp/Muse---Time-is-Running-Out.png` | `spotify:track:2takcwOaAZWiXQijPHIx7B` (EC H) | Former play-and-dash marker; current single-row marker not yet live-validated | Marker recheck open |
| Album | Not recorded | Not recorded | Not recorded | Not recorded | Not recorded | Not recorded | Not recorded | Open |
| Playlist | Not recorded | `None` by model contract; live selection not recorded | Not recorded | Not recorded | Not recorded | Not recorded | Not recorded | Open |

## CM-1 screen-scanner evidence — open

- Selected normalized URI: not recorded.
- Downloaded review file and viewer scale/setting: not recorded.
- Actual presentation-scanner output: not recorded.
- Exact-match result: not recorded.

## CM-1 print, laminate, and final-scan evidence — open

- Printer make/model: not recorded.
- Printing application and version: not recorded.
- Explicit scale setting: not recorded.
- Paper: not recorded.
- Orientation: not recorded.
- Measured finished width and height: not recorded; no size is inferred from PNG DPI.
- Lamination confirmation: not recorded.
- Selected normalized URI: not recorded.
- Actual post-lamination scanner output: not recorded.
- Exact-match result: not recorded.

## Remaining release checklist

- [x] Exercise the immediate-preview flow in the target local browser and confirm
  selection performs one render, the review is fluid across desktop/tablet/mobile,
  and download reuses the same Blob without another render request (Playwright,
  2026-08-13).
- [ ] Configure live Spotify credentials and record one selected track, album, and
  playlist with their full labels and normalized URIs.
- [ ] Record the independent decoder output for all three live examples.
- [ ] Save one live generated example of each supported type for review.
- [ ] Scan at least one downloaded full-resolution card from a screen with the actual
  presentation scanner and record the viewer setting.
- [ ] Record the printer model, application, scale setting, paper, orientation, and
  measured physical output dimensions from the established workflow.
- [ ] Print and laminate one card, then scan it with the actual presentation scanner.
- [ ] Review Spotify attribution and link-back behavior against the applicable policy
  before any use beyond the private household spike.

Until those items are checked with real evidence, fixture-only progress must not be
reported as a successful spike exit or used to justify a large print run.
