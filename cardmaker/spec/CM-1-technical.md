# CM-1 Technical Design

Status: implementation-ready

## Purpose

This document translates the checked decisions and acceptance criteria in
[`CM-1-requirements.md`](CM-1-requirements.md) into an implementation design for
the current Card Maker spike.

CM-1 keeps the spike's catalog, reference normalization, artwork fetching, QR
encoding and verification, rendering service, and isolated Flask distribution.
It changes the adult-facing browser flow to an immediate verified preview whose
bytes are reused for download, adds refined bottom-left content-type symbols to the
locked renderer, locks the already approved typography and overflow baseline, and
defines how the remaining live and physical evidence is recorded.

The existing
[`cardmaker-spike-technical.md`](cardmaker-spike-technical.md) remains the design
record for the implemented spike. This document is the canonical technical design
for the CM-1 delta and supersedes the spike design where the explicit preview
action or provisional marker-free layout is described.

## Selected Decisions Carried Into This Design

All CM-1 decision gates are closed:

| Decision | Selected design consequence |
| --- | --- |
| D-1 Preview/download interaction | Selecting an item performs one render request and displays the verified PNG in a responsive review grid, up to 50% size. `Download PNG` reuses that Blob without a second render. |
| D-2 Marker set | Album uses a disc with hub/reflection detail, playlist uses three stacked dot-dash rows, and track uses one enlarged dot-dash row. All are smoothly rasterized Pillow geometry at the bottom-left anchor. |
| D-3 Overflow and width | The canvas remains 1200 x 756. Labels shrink in deterministic two-pixel steps to 20 pixels, then use a single Unicode ellipsis. No wider variant is added. |
| D-4 Typography and offsets | The packaged DejaVu Sans regular and bold files, 48/42-pixel starting sizes, and current artwork/text offsets are approved and remain locked. |
| D-5 Physical release gate | Automated completion is necessary but not sufficient. Live Spotify, screen scanner, measured print, lamination, and final scanner evidence must be recorded before CM-1 is complete. |

The unchecked alternatives in the requirements are not implementation options.
In particular, the trailing notes and CM-2 handoff questions that still phrase
D-3 or D-4 as open are stale relative to the checked decision checklist and the
user's D-4 approval note. This design follows the checked choices.

## Design Goals

- Implement CM-1 as a small extension of the current spike rather than a package
  rewrite.
- Preserve one server-side resolution, artwork fetch, render, and independent QR
  verification per selection.
- Ensure the responsive preview and downloaded file use the bytes returned by the
  same verified render request, with no second render.
- Keep full Spotify labels, artwork, content type, normalized URI, attribution,
  and entity link visible while a download is attempted or retried.
- Add type markers without moving or reducing the QR panel, artwork region, label
  anchors, or canvas.
- Keep all rendered-card and artwork bytes in memory; add no server output path,
  catalog, cache, or session store.
- Keep the Card Maker distribution isolated from the jukebox runtime and retain
  non-Pi development support.
- Make automated completion and the still-manual physical release gate visibly
  distinct.

## Non-Goals

- Uploaded or generated artwork and crop controls.
- A wider card, alternate layout, theme, or free-form design editor.
- A separate preview-generation action or a second render for download.
- Batch generation, ZIP, A4, PDF, print calibration, or saved-card state.
- New Spotify scopes, user authorization, playback control, or library mutation.
- A frontend framework, browser automation stack, asset build pipeline, or new
  runtime dependency.
- Raspberry Pi deployment, a production WSGI process, operator-surface integration,
  or public hosting.
- Changing the Spotify URI contract, QR encoder settings, or jukebox package.
- Inferring physical print size from PNG metadata.

## Current Baseline

CM-1 starts from commit `26b981a` on the `cardmaker-spike` branch and the current
isolated distribution under [`../`](../).

### Implemented runtime

- [`../src/cardmaker/app.py`](../src/cardmaker/app.py) provides the Flask app
  factory, discovery routes, and `POST /api/render`.
- [`../src/cardmaker/service.py`](../src/cardmaker/service.py) already re-resolves
  the selected URI, fetches its associated Spotify artwork, composes one card,
  independently decodes the composed QR, serializes that same image as a PNG, and
  returns the bytes in a `RenderedCard` without writing a file.
- [`../src/cardmaker/adapters/render_pillow.py`](../src/cardmaker/adapters/render_pillow.py)
  owns the locked 1200 x 756 geometry, packaged fonts, contained artwork, and the
  approved shrink-then-ellipsis rule. It does not yet draw type markers.
- [`../src/cardmaker/web/templates/index.html`](../src/cardmaker/web/templates/index.html)
  and [`../src/cardmaker/web/static/app.js`](../src/cardmaker/web/static/app.js)
  currently expose `Create preview`, retain a full-resolution Blob URL, then expose
  a second `Download PNG` control.
- [`../src/cardmaker/models.py`](../src/cardmaker/models.py) already carries the
  supported content type through `CardDraft.item.reference.kind` and represents a
  verified response as `RenderedCard`. No CM-1 model addition is required.
- [`../src/cardmaker/adapters/qr_segno.py`](../src/cardmaker/adapters/qr_segno.py)
  and [`../src/cardmaker/adapters/qr_zxing.py`](../src/cardmaker/adapters/qr_zxing.py)
  already provide independent encoding and exact-value verification.
- [`../src/cardmaker/adapters/spotify_catalog.py`](../src/cardmaker/adapters/spotify_catalog.py)
  and [`../src/cardmaker/adapters/artwork_http.py`](../src/cardmaker/adapters/artwork_http.py)
  already preserve metadata/artwork association, Spotify provenance, bounded
  in-memory fetching, and no-crop artwork handling.

### Implemented verification

The pre-CM-1 baseline passes:

```text
ruff:   all checks passed
mypy:   no issues in 24 source files
pytest: 86 passed
```

The current tests cover the domain, adapters, service, HTTP response, renderer,
golden geometry, exact QR decode, and jukebox URI contract. They do not yet cover
type-marker pixels or the immediate-preview browser shell.

[`../findings/spike-validation.md`](../findings/spike-validation.md) records the
automated spike findings and correctly labels live Spotify, actual scanner, print,
and lamination evidence as incomplete.

## Spec Alignment Notes

### Immediate preview reuses the existing render boundary

The server already returns the only render that has passed independent QR
verification. CM-1 retains that response as a preview Blob as soon as an item is
selected, then reuses it when the adult downloads.

CM-1 therefore does not add a second endpoint or move rendering into the browser.
It changes `/api/render` to an attachment response, displays its Blob through an
object URL, and gives the same URL to a temporary download link. The route still
returns typed JSON on failure so the current selection and metadata remain usable.

### Selection review shows the generated card

FR-1 requires the final verified card alongside the exact unabridged metadata,
normalized URI, Spotify attribution/entity link, and controls at typical
desktop/tablet widths. The same grid stacks metadata below the preview on narrow
screens. The preview is the exact full-resolution response scaled only by CSS;
download does not create another card.

### Physical evidence remains a release gate

Implementation can complete all code and automated checks without credentials,
printer access, lamination, or the actual presentation scanner. That state must be
reported as “automated CM-1 implementation complete; physical release gate open,”
not as CM-1 complete. Only checked evidence in
[`../findings/spike-validation.md`](../findings/spike-validation.md) closes AC-9
through AC-11.

### PNG DPI metadata is not physical scale

The concept says the four visual references contain 72-DPI metadata, while direct
inspection recorded in the spike findings shows that their PNG byte streams have
no `pHYs` chunk. The current service writes 72-DPI metadata and tests it as part of
the spike output contract.

CM-1 does not change that serialization detail because no selected decision
requires it. It also does not use it to calculate print size. The physical record
must contain printer settings and measured card dimensions, as required by D-5 and
FR-8.

## Architecture

The existing boundaries remain intact:

```text
Browser item selection
  -> one POST /api/render {uri}
       -> CardMakerService.render(uri)
            -> normalize and re-resolve Spotify entity
            -> bounded artwork fetch
            -> Segno QR encode
            -> Pillow card render, including type marker
            -> independent zxing decode of composed card
            -> one lossless PNG serialization in memory
       <- attachment response containing that verified PNG
  -> compare response URI with the reviewed selection
  -> one retained Blob URL shown responsively, up to 600 x 378
  -> `Download PNG` reuses that URL; selection/reset revokes it

No relationship is added to the jukebox runtime or process.
```

CM-1 changes only the renderer and adult-facing HTTP/browser presentation around
the existing service use case. Catalog, artwork, reference, QR, configuration, and
process boundaries stay unchanged.

## Runtime Flow

### Discovery and selection

Search and pasted-reference flows remain unchanged:

1. The adult explicitly searches or resolves a pasted Spotify URL/URI.
2. The server returns typed catalog metadata.
3. Selecting an item immediately opens the review, displays its full primary and
   optional secondary labels, normalized URI, content type, Spotify attribution,
   and entity link, and starts one render request when artwork is available.
4. A verified response is shown as the exact card at up to 600 x 378 CSS pixels
   (50% of 1200 x 756). The review reuses the discovery grid's auto-fit behavior:
   metadata/actions sit beside the preview at typical desktop/tablet widths and
   stack below it when the viewport is narrow. Missing artwork keeps download
   disabled; low-resolution artwork keeps the existing warning.
5. Selecting a different item cancels any in-flight render, revokes the previous
   preview URL, clears only preview status, and populates the new review.

Discovery results and input values remain in the page DOM, so a previous success
or failure does not require a server restart or a repeated search.

### Immediate verified preview and download reuse

Selection performs this sequence:

1. Snapshot the selected item's normalized URI and start an `AbortController` for
   this attempt.
2. Clear the review-scoped status, keep download disabled, and leave the full
   selection visible.
3. Send exactly one `POST /api/render` request containing only `{ "uri": <selected
   normalized URI> }`.
4. Let the existing service re-resolve metadata, fetch artwork, render, verify, and
   serialize once. A verification failure returns JSON and no PNG.
5. Before displaying the preview, require a successful `image/png` response whose
   `X-Cardmaker-Spotify-URI` exactly equals both the snapshotted URI and the URI
   still shown by the current selection. Also require the existing width and height
   headers to be `1200` and `756`. A mismatch is treated as a client-visible
   integrity error; neither preview nor download becomes available.
6. Read the response once as a Blob. Derive the local filename from the existing
   `Content-Disposition` parser, falling back to `card.png` only if the header is
   absent or unusable.
7. Create one object URL for that Blob, assign it to the preview image, enable
   `Download PNG`, and retain the suggested filename.
8. On `Download PNG`, attach a temporary `<a download>` with the retained URL and
   filename, click it once, and remove the link without another HTTP request.
9. Revoke the preview URL on selection change, `Make another`, and `beforeunload`.

The preview Blob contains the exact response bytes from the verified render
request, and the browser never calls `/api/render` again for download.

### Failure and retry

- A classified server failure remains a JSON `{code, message}` response and is
  shown in a new review-scoped live-status element.
- A network, response-type, dimension, URI-header, or Blob failure is shown without
  clearing `selectedItem` or the visible metadata; download remains disabled.
- Selecting another result or choosing `Make another` aborts an in-flight attempt.
  An expected browser `AbortError` does not overwrite the newly selected item's
  status with a stale failure.
- Because the server still renders only in memory, no failed path can leave a
  partial server-side PNG.

### Make another

`Make another`:

1. aborts an in-flight render, if any;
2. revokes any outstanding temporary Blob URL;
3. clears the selected item, review status, and success state;
4. hides the review and returns focus to discovery; and
5. leaves the existing search/paste inputs and discovery functionality usable.

No server reset, cookie, browser storage, or session endpoint is involved.

## Module Plan

### Files to modify

| File | CM-1 change |
| --- | --- |
| [`../src/cardmaker/adapters/render_pillow.py`](../src/cardmaker/adapters/render_pillow.py) | Extend the frozen geometry with the bottom-left symbol anchor and refined shape values. Draw the symbol selected by `draft.item.reference.kind` after labels. Keep QR, artwork, font, overflow, and canvas behavior unchanged. |
| [`../src/cardmaker/app.py`](../src/cardmaker/app.py) | Return the existing `/api/render` PNG with attachment disposition. Preserve strict request shape, exact response bytes, URI/dimension headers, no-store behavior, and JSON errors. |
| [`../src/cardmaker/web/templates/index.html`](../src/cardmaker/web/templates/index.html) | Keep the preview first in DOM order and group encoded URI, Spotify credits, status, and actions in the adjacent metadata panel. |
| [`../src/cardmaker/web/static/app.js`](../src/cardmaker/web/static/app.js) | Render on selection, retain one verified preview Blob/filename, reuse it for download, and keep response-integrity, abort/stale-selection, cleanup, and repeat-card handling. |
| [`../src/cardmaker/web/static/style.css`](../src/cardmaker/web/static/style.css) | Reuse the discovery grid's auto-fit rule so preview and metadata are adjacent at desktop/tablet widths and stacked on narrow screens. Keep the preview responsive and no larger than 50%. |
| [`../tests/test_renderer.py`](../tests/test_renderer.py) | Add marker coverage for every content type, preserve no-secondary playlist behavior, assert fixed marker bounds, retain overflow tests, and update the approved full-card fixture assertion. |
| [`../tests/test_golden_geometry.py`](../tests/test_golden_geometry.py) | Freeze the shared marker anchor and assert the original QR/canvas/content anchors are unchanged. The four historical masters remain unchanged. |
| [`../tests/test_service.py`](../tests/test_service.py) | Exercise verified PNG generation for track, album, and playlist drafts and retain exact decoded URI/no-file behavior. |
| [`../tests/test_app.py`](../tests/test_app.py) | Assert preview-first DOM order and 50% dimensions, one `Download PNG` shell action, attachment response semantics, one render call, Blob reuse, no-store, and preserved error envelopes. |
| [`../tools/create_approved_fixture.py`](../tools/create_approved_fixture.py) | Generate the same deterministic track fixture with its marker. Preserve the refusal to overwrite an approved fixture unless the explicit `--replace-approved` review flag is passed. |
| [`../findings/spike-validation.md`](../findings/spike-validation.md) | Record the locked CM-1 geometry and typography, candidate/approved comparison, automated results, live examples, independent decodes, screen scan, print settings, measured dimensions, lamination, and final scan. Leave unavailable evidence unchecked. |

### Files that do not need runtime changes

- [`../src/cardmaker/models.py`](../src/cardmaker/models.py): content type and
  verified PNG bytes are already represented.
- [`../src/cardmaker/service.py`](../src/cardmaker/service.py): it already performs
  one render and exact independent verification before serialization.
- [`../src/cardmaker/references.py`](../src/cardmaker/references.py): normalized URI
  behavior is already correct.
- The Spotify catalog, artwork fetcher, QR encoder/verifier, settings, entrypoint,
  package dependencies, and jukebox package remain unchanged.
- The historical golden PNGs under [`../../docs/cards/`](../../docs/cards/) are
  evidence, not generated outputs to rewrite.

## Data Model

CM-1 adds no persistent or transport data model.

- `CatalogItem.reference.kind` remains the authoritative marker discriminator.
- `CardDraft` remains Spotify-only and continues to carry in-memory RGB artwork.
- `RenderedCard` remains the verified response value with PNG bytes, normalized
  URI, safe filename, width, and height.
- The `/api/render` request remains the strict one-field JSON object `{ "uri":
  string }`; browser labels, artwork URLs, filenames, kinds, and geometry are not
  accepted as render inputs.

The renderer must not accept a separate marker kind that could drift from the URI
and catalog item.

## Card Layout and Marker Design

### Locked existing geometry

The following current `CardGeometry` values remain unchanged:

| Element | Value |
| --- | --- |
| Canvas | 1200 x 756 RGB, solid black |
| QR panel | 676 x 676 at `(40, 40)` |
| QR/content gap | 40 pixels |
| Content column | `x = 756`, width 404 |
| Artwork box | `x = 756`, `y = 40`, maximum 404 x 453, aspect-preserving contain |
| Primary draw origin | `(756, 513)`, packaged DejaVu Sans Bold, initial 48 px |
| Secondary draw origin | `(756, 578)`, packaged DejaVu Sans, initial 42 px |
| Text fitting | Decrease by 2 px to 20 px, then single-line Unicode ellipsis |

The shared symbol is bottom-aligned to the locked 40-pixel margin:

```text
marker_x = content_x = 756
marker_y = canvas_height - margin - marker_height = 756 - 40 - 36 = 680
```

Every marker is drawn directly by `ImageDraw` in `(255, 255, 255)` on the final
RGB card through a 4x grayscale mask reduced with Lanczos for smooth edges. Marker
drawing occurs only in the content column after the QR panel has been pasted.

### Exact marker geometry

Coordinates below are relative to the 56 x 36 marker box at `(756, 680)`.

| Type | Geometry |
| --- | --- |
| Album | 36-pixel disc with a 3-pixel outline, 10-pixel hub, 4-pixel center hole, and translucent reflection wedge from 300° through 344°. |
| Playlist | Three 5-pixel dots at relative `y = 7, 19, 31` with 4-pixel rounded lines of widths 30, 34, and 26. |
| Track | One 10-pixel dot at relative `(1, 13)` followed by a 31 x 5 rounded dash at `(17, 15)`. |

These shapes share `x = 756`, fit within `x = 756..811` and `y = 680..715`, and
bottom-align immediately above the locked 40-pixel margin. They are separated from
the maximum-size secondary font ink area and leave the QR panel untouched.

The implementation should use one private renderer helper such as
`_draw_content_marker(card, kind, geometry)`. All coordinates and dimensions stay
with the frozen renderer geometry; route and browser code contain no marker
constants. An unknown kind is an invariant violation and must fail rendering rather
than silently omit a marker, although `SpotifyReference` already prevents such a
kind in normal flow.

### Approval boundary

The four historical golden masters have no CM-1 marker and must not be replaced.
The implementation first renders candidate track, album, and playlist cards beside
those masters and the existing approved synthetic fixture. The exact candidate
geometry above is accepted only if the marker meanings are legible and subordinate
at full image size and in the established physical workflow.

If side-by-side review requires a marker-coordinate change, update this section and
the geometry tests before replacing
[`../tests/fixtures/approved-card.png`](../tests/fixtures/approved-card.png). The
approved fixture changes once, intentionally, after review; the generation tool
continues to refuse silent overwrite.

## HTTP and Browser Design

### `POST /api/render`

The route contract remains:

```http
POST /api/render
Content-Type: application/json

{"uri":"spotify:<track|album|playlist>:<22-character-id>"}
```

Successful response:

- status `200`
- `Content-Type: image/png`
- `Content-Disposition: attachment; filename...`
- `Cache-Control: no-store`
- `X-Cardmaker-Spotify-URI: <normalized URI>`
- `X-Cardmaker-Width: 1200`
- `X-Cardmaker-Height: 756`
- body equal to `RenderedCard.png_bytes`

Changing `as_attachment=False` to `as_attachment=True` is the only required route
behavior change. It does not create a file or a second render. Expected and
unexpected error mapping remains unchanged.

### Browser state

`app.js` retains only small coordination state:

- `selectedItem`: the currently reviewed catalog item;
- `activeRenderController`: the current request cancellation boundary, or `null`;
- `previewObjectUrl`: the verified PNG Blob URL currently displayed, or `null`;
- `previewFilename`: the response's safe suggested filename, or `null`.

The page retains only the current verified preview in browser memory. Selection
change, reset, and unload revoke its object URL; the server remains in-memory and
stateless.

### Review controls

The review contains:

- one generated `<img id="card-preview">` displayed responsively at up to
  600 x 378 CSS pixels;
- a metadata/action panel beside it at desktop/tablet widths and below it on narrow
  screens;
- one primary `<button id="download-png">Download PNG</button>`;
- one review-scoped `role="status"`/`aria-live="polite"` element for render and
  verification results; and
- one secondary `Make another` button.

There is no `Create preview` control, persistent download `<a>`, or second render
action in the page shell.

## Configuration and Dependency Design

CM-1 adds no configuration or dependency.

The current variables remain the complete configuration surface:

- `CARDMAKER_SPOTIFY_CLIENT_ID`
- `CARDMAKER_SPOTIFY_CLIENT_SECRET`
- `CARDMAKER_SPOTIFY_MARKET`
- optional `CARDMAKER_HTTP_BIND`
- optional `CARDMAKER_HTTP_PORT`
- optional `CARDMAKER_LOG_LEVEL`

Flask, Pillow, Segno, and `zxing-cpp` remain confined to
[`../pyproject.toml`](../pyproject.toml). No dependency is added to the root jukebox
distribution. Font and marker geometry remain versioned package resources/code,
not environment settings.

## Feedback and Logging Design

### Browser feedback

- Discovery errors continue to use the discovery status area.
- Download progress, verification/render failures, integrity failures, and success
  use the review-scoped status so the current selection remains visible beside the
  feedback.
- A success message states that the download started; it must not claim that the
  browser saved, printed, laminated, or scanned the file.
- The existing artwork-unavailable and low-resolution messages remain visible and
  specific.

### Server logging

Existing log boundaries are sufficient:

- `card_render_succeeded` continues to include only content type and dimensions.
- classified failures continue as `cardmaker_request_failed error_code=...`.
- no URI, full label, filename, artwork URL/body, PNG bytes, token, secret,
  authorization header, or upstream response body is added to CM-1 logs.

No analytics, download history, background polling, or automatic retry is added.

## Testing Strategy

### Renderer and geometry tests

Update [`../tests/test_renderer.py`](../tests/test_renderer.py) to cover:

- exact white-pixel bounds and representative interior/background pixels for the
  album ring, playlist rows, and single track row;
- the shared bottom-left anchor with marker box `(756, 680)..(811, 715)`;
- album hub/reflection detail and smooth deterministic edges;
- playlist rendering with no secondary label and a marker at the fixed bottom;
- track and album secondary labels remaining above the marker;
- identical marker output for repeated controlled inputs;
- unchanged 1200 x 756 RGB canvas, QR panel, artwork containment, packaged fonts,
  and shrink-then-ellipsis behavior; and
- pixel equality with the deliberately replaced CM-1 approved fixture.

The playlist assertion keeps the secondary-label band empty above the fixed
bottom-left marker.

Update [`../tests/test_golden_geometry.py`](../tests/test_golden_geometry.py) to
freeze the new marker anchor while retaining every current QR/canvas/content
assertion. Do not make the historical marker-free masters fail for lacking CM-1
markers.

### Service and QR tests

Extend [`../tests/test_service.py`](../tests/test_service.py) with controlled track,
album, and playlist items. For each type:

- the returned image is exactly 1200 x 756 RGB;
- the independently decoded PNG value equals that item's normalized URI;
- the expected marker occupies the locked marker region; and
- no server-side output file is created.

Retain mismatched decode rejection, missing artwork rejection, filename safety,
Spotify re-resolution, and DPI/metadata checks. QR encoder/verifier behavior itself
does not change.

### HTTP and browser-shell tests

Update [`../tests/test_app.py`](../tests/test_app.py) to assert:

- the page contains one `Download PNG` action and `Make another`;
- the page keeps the preview before encoded URI, Spotify credits, and actions in DOM
  order;
- the stylesheet shares one auto-fit grid rule between discovery and review;
- browser checks cover side-by-side desktop/tablet and stacked narrow/mobile
  geometry; no `Create preview` control exists;
- the render response uses attachment disposition, remains `image/png` and
  `no-store`, and returns exactly the stub service bytes;
- one request results in one `service.render` call;
- URI and dimension headers remain present;
- strict JSON shape and all error envelopes remain unchanged; and
- selection triggers Blob creation once; the download click reuses its object URL;
- object-URL revocation and low-resolution review behavior remain covered.

CM-1 does not add Node, Playwright, Selenium, or another browser runtime solely for
this small vanilla-JavaScript delta. The HTTP contract and page shell are automated;
the target-browser click/download behavior is included in the manual CM-1 workflow
check.

### Full automated gate

Run the repository virtualenv commands:

```sh
cd cardmaker
.venv/bin/ruff check src tests tools
.venv/bin/mypy
.venv/bin/pytest
.venv/bin/python tools/inspect_golden_masters.py
```

The approved fixture may change only for a reviewed CM-1 marker decision. No
other unexplained pixel difference is accepted.

## Live and Physical Validation Design

[`../findings/spike-validation.md`](../findings/spike-validation.md) remains the
single validation record. Add a CM-1 section with the following evidence.

### Live type table

Record one row for each of track, album, and playlist:

- full primary and secondary labels (`None` for playlist);
- normalized Spotify URI;
- browser-downloaded filename and retained review-file location;
- independent `zxing-cpp` decoder output; and
- confirmation that the visible marker matches the selected type.

The Card Maker does not gain an evidence-output directory. These are ordinary
adult-initiated browser downloads. The existing [`../../docs/cards/new/`](../../docs/cards/new/)
may be used as the adult-selected review location, but the application must not
write to it. Fixtures cannot be described as live evidence.

### Screen scanner record

For at least one full-resolution CM-1 card, record:

- the selected normalized URI;
- the actual presentation scanner output; and
- whether the output matched exactly.

Display the reviewed card at a known viewer setting and present it to the scanner;
record whether the actual scanner returns the exact normalized URI.

### Print, laminate, and scan record

For at least one card, record all required physical facts:

- printer make/model;
- printing application and relevant version;
- explicit scale setting;
- paper;
- orientation;
- measured finished width and height;
- confirmation that the card was laminated;
- selected normalized URI;
- actual post-lamination scanner output; and
- exact-match result.

Do not derive or fill the physical dimensions from 72-DPI metadata. If any item is
unknown or a scan fails, leave the corresponding gate incomplete and record the
observed result honestly.

## Failure Handling

| Failure | Required behavior |
| --- | --- |
| No usable Spotify artwork | Keep download disabled; preserve selection and explain that CM-1 is Spotify-artwork-only. |
| Spotify auth, forbidden, not-found, rate-limit, or availability failure | Preserve the current query/selection as applicable; show the existing typed message; never auto-retry. |
| Artwork fetch/decode failure | Return `artwork_unavailable`; start no download; retain selection for retry or replacement. |
| Renderer invariant or unknown content type | Return a safe `internal_error`; emit no partial PNG and do not omit the marker silently. |
| QR missing, extra, or mismatched | Return `qr_verification_failed` with status 422; no PNG response or browser download. |
| Response MIME, URI, width, or height mismatch | Browser rejects the response locally, revokes any Blob URL, and shows an integrity error. |
| Selection changes during render | Abort or discard the stale attempt; never download it under the new review. |
| Browser download setup fails | Revoke temporary state, preserve selection, show an honest error, and allow manual retry. |
| Physical screen/print/lamination scan fails | Record the failure and keep CM-1 incomplete; do not weaken automated QR or physical acceptance criteria. |

## Implementation Sequence

1. Extend the frozen renderer geometry and implement all three marker shapes behind
   the existing `CardRenderer` boundary.
2. Add exact marker, shared-anchor, no-overlap, playlist-no-secondary, and unchanged
   QR/layout tests. Generate candidate renders; do not replace the approved fixture
   yet.
3. Change `/api/render` to attachment disposition and update its HTTP tests without
   changing `CardMakerService.render` or its one-render verification sequence.
4. Replace the explicit preview action with auto-render on selection, a responsive
   preview/metadata grid, Blob reuse for download, stale-request protection,
   cleanup, and `Make another` reset.
5. Update browser-shell, service, and regression tests. Run ruff, mypy, pytest, and
   the golden inspector.
6. Compare the three marker candidates and representative short/long labels beside
   the historical masters. Confirm the already selected font, offsets, 1200-pixel
   width, and shrink-then-ellipsis rule; tune only marker geometry if the recorded
   comparison requires it.
7. Update this design if marker coordinates changed, then deliberately replace the
   approved synthetic fixture and record the final geometry/comparison in the spike
   findings. Run the full automated gate again.
8. With live credentials, download and retain one track, album, and playlist;
   independently decode each and complete the live type table.
9. Complete and record the actual screen-scanner check.
10. Print at an explicit setting, measure, laminate, scan, and record every physical
    field required by FR-8 and AC-11.
11. Report CM-1 complete only when both the automated gate and all live/physical
    evidence are complete. Otherwise report the exact remaining gate.

## Open Risks

- The fixed marker proportions are visually grounded in the bottom-left region but
  still require the specified side-by-side and physical review before
  the fixture is approved.
- Some browser security settings may block a programmatic download after an
  asynchronous fetch. The target local browser must be exercised; a failure should
  be recorded and fixed without reintroducing a second production action.
- Marker legibility after the established print and lamination workflow cannot be
  inferred from full-resolution pixels.
- Live Spotify availability, development-mode app access, or rate limiting may
  delay AC-9 without invalidating fixture-based automated progress.
- The historical golden masters differ in typography, artwork height, and QR edge
  rasterization. CM-1 intentionally preserves one deterministic baseline rather
  than recreating their per-card variations.
- Physical print scale remains unknown until measured evidence is recorded. A
  large card run must not rely on PNG DPI metadata.

There are no open CM-1 product decisions blocking implementation.
