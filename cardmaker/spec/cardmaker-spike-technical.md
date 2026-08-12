# Jukebox Card Maker Spike Technical Design

## Purpose

This document turns the Quick Spike Proposal in
[`cardmaker-concept.md`](cardmaker-concept.md) into an implementation-shaped design.
The spike must answer whether an adult can move from Spotify search or a pasted
Spotify reference to a correctly labelled, scannable card matching the existing
golden masters closely enough to support the established print workflow.

The implementation is deliberately small, but it is not throwaway. It establishes
the package, domain types, adapter boundaries, and deterministic renderer that a
later Card Maker can extend. The browser route and client-side coordination are the
permitted rough stitching layer.

There is no separate Card Maker requirements document. This design therefore uses
the checked-in concept, its explicit spike scope, and the runtime direction supplied
with this design request as the selected decisions.

## Selected Decisions Carried Into This Design

- The Card Maker is an adult-operated browser application.
- It is a separate application and service. It does not import, call, supervise, or
  share mutable state with the jukebox controller at runtime.
- The Raspberry Pi 3 is the default eventual host, but the same application package
  must run on a laptop and remain deployable behind a hosted Python web process.
- The spike is first validated on a laptop so Pi deployment does not consume the
  half-day-to-one-day evidence timebox.
- The spike supports Spotify search plus pasted Spotify URLs and URIs for tracks,
  albums, and playlists.
- The spike uses Spotify-provided metadata and artwork only.
- The output is one RGB PNG at a time using the locked 1200 x 756 layout.
- Pillow and Segno are isolated Card Maker dependencies, not jukebox runtime
  dependencies.
- QR verification is real decoding, not an assertion that the encoder received the
  expected string.
- No generated or uploaded artwork, project persistence, card library, batch sheet,
  PDF output, or printer-calibration UI is added to the spike.
- The workflow must be quick to repeat for many cards without restarting the server,
  even though it still downloads cards one at a time.

## Design Goals

- Leave behind a usable single-card workflow rather than a disposable demo.
- Keep the domain and side-effect boundaries small enough to understand in one
  sitting.
- Make output independent of the operating system's installed fonts and image
  tools.
- Keep all secrets and Spotify Web API authorization server-side.
- Avoid background Spotify requests, durable metadata caching, and artwork archives.
- Keep memory and dependency costs reasonable for a Raspberry Pi 3.
- Make live Spotify behavior replaceable by fixtures in automated tests.
- Preserve exact normalized Spotify URIs so generated cards remain compatible with
  the existing jukebox parser.

## Non-Goals

- Production hardening, public internet exposure, or multi-user authorization.
- Integration into the existing operator HTTP server or its pages.
- Reuse of the playback backend for catalog access.
- Any playback controls or Spotify library mutations.
- A frontend framework, asset build pipeline, or component library.
- A generic plugin architecture for future cover providers.
- Solving the wider-card variant or final long-label product behavior.
- Automating physical print layout before the successful physical scale is recorded.

## Current Baseline

The repository currently has one Python distribution in
[`../../pyproject.toml`](../../pyproject.toml). Its `src/jukebox` package has no
mandatory third-party runtime dependencies. Card Maker rendering and web
dependencies must not be added to that distribution.

Relevant existing evidence is:

- [`../../scripts/generate.py`](../../scripts/generate.py) proves the broad canvas,
  QR-panel, artwork, and two-line text composition. It is forensic input, not a base
  module: it accepts a prebuilt QR, silently crops artwork, selects fonts from the
  host, and mixes argument handling with rendering.
- [`../../scripts/generate_validation_cards.py`](../../scripts/generate_validation_cards.py)
  contains another printable-card path, but its white control-card design and
  platform rasterization tools are not part of the music-card renderer.
- The four PNGs under [`../../docs/cards`](../../docs/cards) are the visual golden
  masters named by the concept. Each is 1200 x 756 RGB.
- [`../../src/jukebox/core/parser.py`](../../src/jukebox/core/parser.py) defines the
  playback application's accepted Spotify URI contract.
- [`../../src/jukebox/adapters/playback_spotify.py`](../../src/jukebox/adapters/playback_spotify.py)
  demonstrates token caching and honest Spotify error mapping, but it is coupled to
  player and device behavior and must not be imported by Card Maker.
- [`../../src/jukebox/operator_server.py`](../../src/jukebox/operator_server.py) is a
  useful example of a small local browser surface. Card Maker needs multipart-ready
  request handling later, so it should not extend that server.
- The existing operator server uses port 8080. Card Maker needs a distinct address
  and lifecycle.

## Resolved Tensions and Explicit Assumptions

### Spike isolation versus the Pi as the default host

The concept excludes Pi deployment from the spike, while the intended product shape
defaults to running on the jukebox Pi.

Resolution: the spike creates an independently installable, environment-configured
WSGI application with no laptop-specific behavior. Laptop execution and physical
card validation are spike scope. A `systemd` unit and Pi deployment scripting are a
post-spike task and must not require package restructuring.

### Existing Spotify authorization versus catalog-only access

The spike needs public catalog search and entity lookup, not user data or playback
control. It uses Spotify's server-to-server client credentials flow with the same
Spotify application ID and secret values already available to the operator, copied
into Card Maker's own environment namespace. It does not consume the jukebox refresh
token or playback scopes.

Because this token has no user country, `CARDMAKER_SPOTIFY_MARKET` is required for
live use. No country is guessed. The current Spotify Search API considers content
unavailable when neither a market nor user country is supplied.

### Repetition versus excluded batch features

The target weekend workflow may involve more than 100 cards, but sheet layout,
batch export, and saved projects remain excluded.

Resolution: after a download the page stays usable, keeps the server running, and
offers a direct “make another” reset. Each preview is downloadable without a second
render. No server-side card collection or ZIP file is introduced.

### Locked golden layout versus unresolved typography

The existing generator's 48-pixel bold and 42-pixel regular sizes are useful clues,
not final truth. The exact typefaces and offsets have not yet been recovered.

Resolution: golden-master measurement is the first implementation slice. The spike
then commits or packages one redistributable regular/bold font pair and addresses it
by package resource. If the exact reference font cannot legally be distributed, the
findings record the deliberate mismatch and choose one deterministic open font. The
renderer must never search host font directories or silently fall back.

### QR sharpness versus a fixed 676-pixel panel

QR versions can have different module counts, and 676 is not divisible by every
possible symbol width.

Resolution: `QrEncoder` renders modules at the largest integer pixel scale that fits
inside the recovered QR area, including the fixed quiet zone, and centers the result
inside the 676 x 676 white panel. It never resizes a rasterized QR. Golden-master
recovery fixes the error-correction level, quiet-zone module count, and panel corner
radius before the renderer constants are considered settled.

### Spotify artwork rules versus the old generator

The old generator center-crops artwork. The concept and current Spotify design
guidance prohibit cropping or distorting Spotify-provided artwork.

Resolution: the spike uses a contain operation with aspect ratio preserved and a
black remainder where needed. It never uses `center_crop_resize()` for Spotify
artwork. The browser result and review surface includes Spotify attribution and a
link to the selected Spotify entity. Attribution on the downloaded physical card
remains the product/policy question already recorded in the concept and must be
resolved before wider distribution.

## Architecture

```text
Browser (plain HTML/CSS/JS)
  -> Flask routes in app.py                         rough stitching boundary
       -> CardMakerService
            -> SpotifyCatalog                      live catalog adapter
            -> SpotifyReferenceParser              URI/URL normalization
            -> ArtworkFetcher                      bounded in-memory HTTP fetch
            -> SegnoQrEncoder                      exact normalized URI
            -> ZxingQrVerifier                     independent decode check
            -> PillowCardRenderer                  deterministic RGB PNG

Automated tests
  -> Flask test client
       -> CardMakerService
            -> FixtureCatalog / FixtureArtworkFetcher
            -> real QR encoder, verifier, and renderer where relevant

Runtime isolation
  cardmaker process :8081  -- no calls/imports -->  jukebox process :8080
```

The concrete package layout is:

```text
cardmaker/
  pyproject.toml
  README.md
  src/cardmaker/
    __init__.py
    __main__.py
    app.py
    config.py
    models.py
    references.py
    service.py
    adapters/
      __init__.py
      artwork_http.py
      qr_segno.py
      qr_zxing.py
      render_pillow.py
      spotify_catalog.py
    assets/fonts/
      <selected-regular-font>
      <selected-bold-font>
    web/
      templates/index.html
      static/app.js
      static/style.css
  tests/
    fixtures/spotify/
    fixtures/artwork/
    test_app.py
    test_references.py
    test_service.py
    test_spotify_catalog.py
    test_qr.py
    test_renderer.py
    test_golden_geometry.py
  tools/
    inspect_golden_masters.py
  findings/
    spike-validation.md
```

This is a second Python distribution inside the same repository. Its virtualenv is
`cardmaker/.venv` locally and a separate environment under its eventual Pi install.
The root `jukebox` distribution does not depend on `cardmaker`, and `cardmaker` does
not depend on `jukebox`.

## Core Interfaces and Data Model

Only interfaces with two real implementations or an important side-effect boundary
are made explicit. The spike does not add abstract base classes for every helper.

### Spotify reference

`SpotifyReference` is an immutable value with:

- `kind`: `track`, `album`, or `playlist`
- `spotify_id`: the validated base-62 identifier
- `uri`: canonical `spotify:<kind>:<id>`
- `external_url`: canonical `https://open.spotify.com/<kind>/<id>`

`SpotifyReferenceParser` accepts supported Spotify URIs and `open.spotify.com` share
URLs, removes query parameters and fragments, and emits the canonical value. It
rejects short links, artist links, episodes, local files, extra path content, and
unknown hosts. An optional leading Spotify locale path such as `intl-de` may be
accepted, but it is removed from the canonical reference.

The parser is intentionally duplicated rather than imported from `jukebox`; a
cross-package contract test proves its normalized URIs are accepted by the jukebox
parser.

### Catalog item

`CatalogItem` is the only catalog representation exposed above the adapter:

- `reference: SpotifyReference`
- `primary_label: str`
- `secondary_label: str | None`
- `artwork: ArtworkReference | None`
- `external_url: str`

Label mapping follows the concept exactly:

| Type | Primary | Secondary | Artwork |
| --- | --- | --- | --- |
| track | artist names in Spotify response order, joined with `, ` | track name | album image |
| album | artist names in Spotify response order, joined with `, ` | album name | album image |
| playlist | playlist name | `None` | playlist image |

The adapter preserves Spotify's supplied spelling and Unicode. It does not invent a
playlist owner subtitle. Full, untruncated metadata stays visible in the browser even
when the rendered card needs a deterministic fit rule.

`ArtworkReference` holds the Spotify-provided URL and optional reported dimensions.
It is provenance, not downloaded bytes, and is never accepted from a browser render
request.

### Card draft and render result

`CardDraft` holds a resolved `CatalogItem` and the fetched in-memory RGB artwork.
It includes a `cover_source="spotify"` discriminator now so upload and generated
cover variants can become explicit union members later. No inactive provider classes
or routes are added in the spike.

`RenderedCard` holds PNG bytes, the normalized URI, output filename, width, and
height. It does not write a file on the server.

### Side-effect protocols

- `SpotifyCatalog.search(query) -> tuple[CatalogItem, ...]`
- `SpotifyCatalog.resolve(reference) -> CatalogItem`
- `ArtworkFetcher.fetch(reference) -> RGB image`
- `QrEncoder.encode(uri) -> monochrome image`
- `QrVerifier.decode(image) -> str`
- `CardRenderer.render(draft, qr_image) -> RGB image`

`FixtureCatalog` and `FixtureArtworkFetcher` are honest test adapters backed by
checked-in Spotify-shaped fixtures. They are not selectable in the normal web app
and never fabricate live-search success.

## Card Maker Service

`CardMakerService` owns the application use cases so HTTP routes remain glue:

1. `search(query)` validates a non-empty bounded query and delegates to the catalog.
2. `resolve(raw_reference)` normalizes the reference and resolves fresh Spotify
   metadata.
3. `render(raw_uri)` normalizes the URI, resolves metadata server-side, fetches its
   artwork, generates the QR, composes the card, independently decodes the QR from
   the composed card, and returns PNG bytes only if the decoded value exactly equals
   the normalized URI.

The render endpoint does not accept labels, an artwork URL, layout coordinates, or
a filename from the browser. This prevents metadata drift, arbitrary server-side URL
fetches, and layout variants from leaking into the spike API.

## Spotify Catalog Adapter

`SpotifyCatalog` uses standard-library HTTP underneath a narrow requester function,
matching the existing repository's testable adapter style. A new general-purpose
HTTP client dependency is not needed for three JSON operations.

### Authorization

- Read `CARDMAKER_SPOTIFY_CLIENT_ID` and
  `CARDMAKER_SPOTIFY_CLIENT_SECRET` from the server environment.
- Request an app access token through the client credentials flow.
- Cache it in memory until shortly before the returned expiry.
- Refresh on demand only; do not poll.
- Never serialize tokens, authorization headers, or client secrets into logs,
  responses, cookies, HTML, or PNG metadata.

### Search and lookup

- Search `/v1/search` for `track,album,playlist` with the configured market.
- Use a fixed spike limit of five results per type. The browser groups the returned
  items by type rather than requesting an unbounded feed.
- Resolve pasted references through the corresponding track, album, or playlist
  entity endpoint.
- Select the largest available Spotify image for rendering; a smaller preview may be
  displayed by the browser.
- Carry Spotify's entity URL through to the browser for attribution and review.

The current Search API maximum is ten results per item type, so the fixed limit of
five is within the documented contract and avoids unnecessary calls.

### Error mapping

The adapter returns typed application errors rather than leaking raw upstream JSON:

| Upstream condition | Application code | Browser behavior |
| --- | --- | --- |
| token rejected / 401 | `spotify_auth_failed` | show configuration/auth error |
| unavailable or forbidden / 403 | `spotify_forbidden` | explain item/app cannot access content |
| entity missing / 404 | `spotify_not_found` | keep reference field editable |
| rate limited / 429 | `spotify_rate_limited` | show `Retry-After`, do not auto-retry |
| timeout/DNS/5xx | `spotify_unavailable` | retain user input and offer manual retry |
| empty search | `no_results` | show an empty result state, not an error page |
| no usable image | `artwork_unavailable` | block spike render and explain follow-up sources are excluded |

There is no automatic search-as-you-type. Search runs on form submission, and the
application performs no background retry or polling.

## Artwork Fetching

`ArtworkHttpFetcher` receives an `ArtworkReference` produced by the catalog adapter;
it never receives a raw browser URL. It:

- allows HTTPS only
- applies a short connection/read timeout and a bounded response size
- accepts supported raster content types only
- decodes with Pillow's decompression-bomb protection enabled
- converts to RGB in memory
- closes the upstream response and source image promptly
- does not persist bytes or create a cache directory

The renderer uses aspect-preserving containment. Spotify artwork is not cropped,
stretched, blurred, recolored, extended, or overlaid.

## QR Encoding and Verification

`SegnoQrEncoder`:

- accepts only a previously normalized supported Spotify URI
- produces a standard QR code with black modules on white
- uses the recovered, pinned error-correction and quiet-zone settings
- paints every module as an integer-aligned rectangle
- returns the QR panel at its final size; no later resampling is allowed

`ZxingQrVerifier` uses the small `zxing-cpp` Python binding to decode the final
composed card image independently from Segno. The verifier must find exactly one QR
whose text exactly matches `CardDraft.item.reference.uri`. A missing, extra, or
mismatched QR aborts rendering with `qr_verification_failed`; the browser never
enables download for that preview.

The dependency remains Card Maker-only. Current Raspberry Pi Python wheel indexes
publish ARMv7 wheels for Python 3.11, which fits the Pi 3 target without adding
OpenCV.

## Deterministic Card Rendering

All geometry lives in one frozen `CardGeometry` value in `render_pillow.py`; route
code and JavaScript contain no drawing constants.

### Locked baseline

- canvas: 1200 x 756 RGB
- background: solid black
- outer margin: 40 pixels
- QR panel: 676 x 676 at `(40, 40)`
- content column: starts at `x = 756`, baseline width 404 pixels
- artwork: top-aligned at `y = 40`, aspect ratio preserved
- text: white and left-aligned at `x = 756`
- primary: packaged bold font
- secondary: packaged regular font
- playlist: primary line only
- PNG metadata: 72 DPI for parity with the golden files, explicitly not a print-size
  definition

`inspect_golden_masters.py` is a development tool, not a runtime dependency. It
reports non-black region bounds, QR panel bounds, artwork bounds, text bounds, and
PNG metadata for all four masters. Its measured constants and a side-by-side review
are committed to `findings/spike-validation.md`.

### Text overflow shortcut

The spike stays on the 1200-pixel baseline and does not add a wider card. It starts
from the recovered font sizes, reduces by deterministic two-pixel steps down to the
recovered minimum, then applies a single-line ellipsis if needed. It never shrinks or
moves the QR panel. The unabridged labels remain visible in the browser review.

This rule is an explicit spike placeholder. The final width and overflow decisions
remain open in the concept.

### Output filename

The server derives a filesystem-safe name from the Spotify labels. Path separators,
control characters, and trailing dots/spaces are removed. The browser receives the
suggested name but owns the actual local save. No output path comes from the request.

## HTTP and Browser Design

Flask is the one added web framework. It provides a small app factory, routing,
error handling, template/static resource packaging, and later multipart upload
support without a frontend build system. Pillow, Segno, and `zxing-cpp` remain the
only image/QR dependencies.

### Routes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | one adult-facing authoring page |
| `GET` | `/healthz` | local process readiness; never calls Spotify |
| `GET` | `/api/search?q=...` | grouped catalog candidates, five per type |
| `POST` | `/api/resolve` | normalize and resolve one pasted URL or URI |
| `POST` | `/api/render` | re-resolve one URI and return verified PNG bytes |

All API errors use a small JSON envelope with `code` and adult-readable `message`.
Unexpected errors receive `internal_error`; tracebacks stay in server logs.

`POST /api/render` returns the PNG inline with a suggested filename and normalized
URI response headers. The browser creates one object URL for the full-resolution
preview. Download reuses that exact blob, proving the reviewed image and saved image
are identical. The previous object URL is revoked when replaced or reset.

### Page flow

The page is one plain template plus small CSS and JavaScript files:

1. Search form and paste field are visible together.
2. Explicit submission calls search or resolve.
3. Results are grouped as Track, Album, and Playlist and show supplied labels,
   artwork, Spotify attribution, and an entity link.
4. Selection shows the exact normalized URI and label mapping.
5. “Create preview” calls render once and displays the 1200 x 756 PNG scaled by CSS.
6. Download is enabled only for the verified preview.
7. “Make another” releases the blob and returns to discovery without reloading the
   server or losing configuration.

The stitching state may live in `app.js`. Domain normalization, catalog mapping,
rendering, QR verification, and error classification must not.

## Configuration Design

Configuration is loaded once by `config.py` into an immutable `Settings` value.

| Variable | Required | Purpose |
| --- | --- | --- |
| `CARDMAKER_SPOTIFY_CLIENT_ID` | live mode | Spotify application ID |
| `CARDMAKER_SPOTIFY_CLIENT_SECRET` | live mode | Spotify application secret |
| `CARDMAKER_SPOTIFY_MARKET` | live mode | explicit two-letter catalog market |
| `CARDMAKER_HTTP_BIND` | no | defaults to `127.0.0.1` |
| `CARDMAKER_HTTP_PORT` | no | defaults to `8081` |
| `CARDMAKER_LOG_LEVEL` | no | defaults to `INFO` |

Font paths, layout coordinates, Spotify API URLs, and fixture mode are not
environment configuration. Fonts and geometry are versioned package resources;
tests inject requesters and fixture adapters directly.

The local run command is one short command after installation:

```sh
cd cardmaker
.venv/bin/python -m cardmaker
```

`python -m cardmaker` uses Flask's Werkzeug server for the spike and makes that
limitation visible in the startup log. The `create_app()` WSGI factory is the stable
entrypoint for a later process server.

## Runtime and Deployment Boundaries

### Laptop spike

- Install only `cardmaker/pyproject.toml` into `cardmaker/.venv`.
- Bind to loopback on port 8081 by default.
- Store credentials only in the launching shell or an ignored local env file loaded
  by the shell; the app does not parse or discover repository secret files.
- Keep all generated images in browser memory until the adult downloads them.

### Raspberry Pi default target after the spike

The intended deployment shape is a separate `cardmaker.service` with:

- its own virtualenv and entrypoint
- its own `/etc/cardmaker/cardmaker.env`
- LAN binding on port 8081
- ordering after `network-online.target`
- no `Requires=`, `PartOf=`, health check, IPC, import, or HTTP relationship with
  `jukebox.service`
- no write access to jukebox state or configuration

The adult reaches `http://jukebox.local:8081/`. Stopping, restarting, upgrading, or
failing Card Maker must not affect scanning or playback. Linking to it from the
operator page can be a later static convenience link, not a service integration.

The spike does not add this unit or change Pi deployment scripts.

### Hosted option

The same `create_app()` factory can run behind a WSGI process server with environment
configuration and ephemeral memory. A public deployment additionally requires TLS
and access control at the hosting/reverse-proxy boundary. The spike does not build
accounts or expose an unauthenticated Card Maker on the public internet.

## Logging, Privacy, and Failure Handling

Logs are concise structured key/value events or ordinary server lines suitable for
local stderr and later `journalctl`:

- `cardmaker_started`
- `catalog_search_succeeded` / `catalog_search_failed`
- `reference_resolved` / `reference_rejected`
- `card_render_succeeded` / `card_render_failed`
- `spotify_rate_limited`

They may include content type, result count, elapsed time, normalized non-secret
error code, and output dimensions. They must not include secrets, access tokens,
authorization headers, raw artwork, PNG bytes, or complete upstream error bodies.

Expected failures stay on the page and preserve the adult's current query or pasted
reference. Configuration errors fail startup with the missing variable named. A
render failure never leaves a partial file because the server writes no output file.

API and PNG responses use `Cache-Control: no-store`. Artwork and metadata live only
for the request plus the in-process access-token cache; there is no local catalog,
recent-card database, analytics, or search history.

## Testing Strategy

### Unit and contract tests

- URI and URL normalization, including query/fragment removal and unsupported types
- label mapping for track, album, and playlist fixtures
- multiple-artist ordering and Unicode preservation
- token reuse until expiry and on-demand refresh
- 401, 403, 404, 429 with `Retry-After`, timeout, malformed JSON, and empty results
- artwork fetch scheme/content/size checks and no-crop containment
- exact 1200 x 756 RGB output and fixed geometry anchors
- packaged regular and bold font loading without host fallback
- deterministic shrink-and-ellipsis behavior
- QR integer-module rendering and independent exact-value decode
- refusal to return a PNG when QR verification fails
- suggested filename sanitization
- normalized Card Maker URIs accepted by the jukebox parser

HTTP tests use Flask's test client with injected fixture adapters. They assert that
credentials and raw upstream failures never appear in HTML, JSON, headers, or PNG
metadata.

### Golden-master tests

Golden tests separate stable geometry from expected content differences:

- assert canvas, panel, column, artwork, and text anchors from the measured masters
- compare a deterministic fixture render to an approved spike fixture
- generate a diff image during manual analysis, but do not make a fragile global
  pixel percentage the only pass/fail signal
- explicitly record font, corner, artwork-fit, and text-offset differences that
  remain after the spike

The existing golden PNGs remain evidence and are not regenerated by tests.

### Manual spike validation

The spike is not complete on automated tests alone. Record in
`findings/spike-validation.md`:

1. The exact run command and environment variable names used.
2. One live search selection and generated example for each supported type.
3. The normalized URI and independent decoder output for all three examples.
4. A side-by-side or diff comparison with the four golden masters.
5. A real scanner read from at least one on-screen preview.
6. The established printer settings and physical output dimensions; do not infer
   them from 72-DPI metadata.
7. A real scanner read after printing and lamination.
8. Any remaining API, typography, geometry, artwork, or workflow finding that should
   change the MVP design.

Live Spotify access is mandatory for success. Fixture-only progress is useful but
must be labelled incomplete.

## Implementation Sequence

Keep each slice independently testable and stop after the spike evidence is
captured:

1. Add the isolated `cardmaker` distribution, app factory, config, health route,
   plain page shell, and one local run command.
2. Measure the four golden masters; pin the packaged fonts and geometry constants;
   add geometry tests before implementing the full renderer.
3. Add reference normalization and domain values, including the cross-package URI
   contract test.
4. Add `SpotifyCatalog` with client-credentials token caching, search, resolve,
   typed errors, and fixtures.
5. Add bounded artwork fetching and the Pillow renderer with the provisional
   deterministic overflow rule.
6. Add Segno QR encoding and independent `zxing-cpp` verification of the composed
   output.
7. Stitch search, paste, selection, preview, download, and “make another” together
   in the routes and vanilla JavaScript.
8. Generate the track, album, and playlist examples; perform golden, scanner, print,
   and lamination checks; write the findings.
9. Stop the spike. Do not start upload, image generation, sheet layout, persistence,
   Pi deployment, or UI polish until the findings are reviewed.

For weekend throughput, steps 1–7 produce the usable authoring loop. Step 8 must
validate at least one physical card before committing a large print run.

## Risks and Follow-Up Decisions

- Spotify policy and quota behavior can change. The browser attribution/link-back
  implementation and any wider distribution must be rechecked against current
  Spotify terms.
- Development-mode Spotify app access or market availability may prevent some
  playlist results even when other types work.
- The exact golden font may not be redistributable; deterministic similarity may be
  the achievable spike result.
- The current print scale is not encoded by the 72-DPI PNG metadata. A 100-card run
  should not begin until one measured print-and-scan check records the real scale.
- `zxing-cpp` has suitable Pi wheels today, but the actual Pi OS architecture must be
  confirmed before Pi deployment.
- One-at-a-time download is workable but may be the first friction exposed by making
  100 cards. Evidence should decide whether the next feature is an in-session card
  queue, ZIP export, or A4/PDF sheet layout.
- Long labels may still look poor under the spike placeholder rule. The browser must
  make truncation visible so it is not discovered after printing.
- A hosted deployment needs external access control and operational limits before it
  is safe to expose.

## Spike Exit

The spike succeeds when all checks in the concept are evidenced and the resulting
code can repeatedly create individual cards without manual URI, QR, or image-file
preparation. Its architectural success criterion is equally important: the catalog,
reference normalization, QR verification, and renderer can move into an MVP without
being disentangled from HTTP route code or the jukebox playback service.
