# Jukebox Card Maker - Concept Specification

Status: draft for refinement

Post-spike delivery is grouped in
[`cardmaker-roadmap.md`](cardmaker-roadmap.md).

## Overview

The Jukebox Card Maker is an adult-operated, local-first browser tool for creating
physical music cards for the QR Card Jukebox.

It helps a parent find a track, album, or playlist on Spotify, choose or create
appropriate artwork, and produce a composed card image containing:

- a standard QR code with the Spotify URI expected by the jukebox
- cover artwork
- the content label
- a compact marker identifying the content as a track, album, or playlist

The tool is an authoring surface for an adult. It is not a child account, child
profile, recommendation engine, or child-operated Spotify browser. Children may
express preferences, help with the physical craft activity, and use the finished
jukebox under parental supervision; the authenticated Spotify user and curator
remain the adult.

This concept extends the product direction in
[`../../spec/concept.md`](../../spec/concept.md). It does not change the existing
scan-to-playback contract.

## Product Goals

- Make creating one new card quick enough that adding music does not feel like a
  technical task.
- Let an adult search Spotify instead of manually finding and transcribing a URI.
- Accept pasted Spotify URLs and URIs as an equally quick alternative to search.
- Populate trustworthy artist, title, and artwork candidates from the selected
  Spotify item.
- Support an original cover image when Spotify artwork is unavailable or not the
  desired visual for the card.
- Reproduce the already tested card layout and QR geometry consistently.
- Make track, album, and playlist cards distinguishable at a glance without
  competing with the title, artwork, or QR code.
- Produce a downloadable image that can enter the existing print and lamination
  workflow.
- Keep Spotify credentials and other secrets out of the browser and repository.
- Keep the implementation lightweight enough for a Raspberry Pi 3 while retaining
  the option to run the tool on a non-Pi development machine.

## Non-Goals

- A child-facing Spotify discovery or account-management experience.
- Automatic recommendations based on a child's behavior or inferred preferences.
- Recording child profiles, listening history, or preference data.
- Replacing the Spotify client or offering audio playback in the Card Maker.
- Editing playlists or managing the adult's Spotify library.
- Changing the jukebox QR payload format.
- A free-form design editor, theme system, or general-purpose graphics application.
- Batch sheet layout, printer calibration, and cutting guides in the first usable
  version. These remain useful follow-up capabilities.

## Operating Model

The Card Maker is opened by an adult in a browser, either from a development
machine or through the jukebox's operator surface on the local network. It is kept
separate from the screenless child playback interaction.

The expected flow is:

1. The adult opens the Card Maker.
2. They search Spotify or paste a Spotify share URL or URI.
3. They choose a track, album, or playlist from the results.
4. The tool normalizes the selection to a supported Spotify URI and fills the
   label metadata.
5. The adult selects Spotify-provided artwork, uploads an image they may use, or
   creates an original cover from an adult-authored description.
6. The selection review shows the exact URI, wording, artwork, and content type.
7. The adult chooses one primary `Download PNG` action. The tool composes and
   verifies the card, then starts the PNG download immediately; there is no
   separate `Create preview` step or second download action.
8. The adult reviews the downloaded card, then prints, cuts, and laminates it
   using the already validated physical workflow.

The tool should prefer sensible defaults and a single clear primary action at each
step. Advanced configuration should not be required for an ordinary card.

## Supported Spotify Content

The supported content types remain aligned with the jukebox parser:

| Spotify type | QR payload | Primary label | Secondary label | Type marker | Default artwork |
| --- | --- | --- | --- | --- | --- |
| Playlist | `spotify:playlist:<id>` | Playlist title | None | Three stacked dot-dash rows | Playlist image |
| Track | `spotify:track:<id>` | Artist | Track title | Right-pointing play mark with a short heavy dash | Track's album artwork |
| Album | `spotify:album:<id>` | Artist | Album title | Disc circle | Album artwork |

Multiple credited artists should be presented using Spotify's supplied metadata,
with a deterministic fit rule to be selected during refinement.

### Discovery

The first discovery surface should use Spotify catalog search for tracks, albums,
and playlists. Results should be grouped or filtered by type so an adult can
distinguish similarly named items quickly. Search pagination is useful, but the
initial experience should show a small result set rather than an unbounded catalog
feed.

The Card Maker should also accept:

- `spotify:track:<id>`
- `spotify:album:<id>`
- `spotify:playlist:<id>`
- corresponding `https://open.spotify.com/...` share URLs

URLs are normalized internally to Spotify URIs before QR generation. Tracking
query parameters from share URLs must not be included in the QR payload.

### Authentication and API Access

Spotify API requests are made by the server-side application. Client secrets,
refresh tokens, and access tokens are never returned to browser code.

The Card Maker may reuse the adult operator's configured Spotify application and
authorization, but catalog access should live behind a dedicated adapter rather
than being coupled directly to the playback backend. This keeps discovery testable
with fixtures and prevents card-authoring changes from destabilizing playback.

The integration must handle expired authorization, unavailable content, empty
results, network failures, `403` responses, and Spotify `429` quota or rate-limit
responses honestly. It must not add background polling.

## Cover Image Sources

The complete Card Maker supports three cover sources.

### Spotify-Provided Artwork

Spotify artwork is the fastest default when it is available. The tool must track
its Spotify provenance and render it without cropping, distortion, filters,
overlays, or generated extensions. Text and the QR code remain in their separate
layout regions.

Spotify metadata and artwork should be fetched only when needed for search,
preview, and rendering. They should not become a permanent local catalog or
artwork archive.

### Adult-Provided Artwork

The adult may upload an image they are permitted to use. The tool may offer a
simple fit preview and an explicit crop for this source because it is not
Spotify-provided artwork. The original upload should not be modified silently.

### Generated Original Artwork

The adult may write a description and request an original cover image from a
configured image-generation provider. The adult reviews and selects the result
before it is placed on a card.

This is an optional provider integration, not a prerequisite for Spotify search or
card rendering. Spotify artwork and Spotify-fetched metadata must not be
automatically sent to an image-generation model. The generation prompt is authored
by the adult and remains visibly editable. Provider credentials remain server-side,
and generation failures or unavailable configuration fall back to upload or
Spotify artwork rather than blocking card creation.

## Locked Card Design

The following tested images are the visual golden masters:

- [`../../docs/cards/laternenlauf_card.png`](../../docs/cards/laternenlauf_card.png)
- [`../../docs/cards/lichterkinder_qr_card_with_art.png`](../../docs/cards/lichterkinder_qr_card_with_art.png)
- [`../../docs/cards/nin_qr_card.png`](../../docs/cards/nin_qr_card.png)
- [`../../docs/cards/willy_astor_qr_card.png`](../../docs/cards/willy_astor_qr_card.png)

The layout is not to be redesigned during implementation. Values recovered from
the reference pixels form the baseline:

- canvas: 1200 x 756 pixels
- background: solid black
- outer margin: 40 pixels
- left QR panel: 676 x 676 pixels, starting at `(40, 40)`
- gap between the QR panel and content column: 40 pixels
- content column start: `x = 756`
- baseline content-column width: 404 pixels, leaving a 40-pixel right margin
- artwork: top-aligned in the content column, aspect ratio preserved
- text: white, left-aligned with the artwork
- primary line: bold
- secondary line: regular
- playlist cards: one bold title line and no invented secondary text
- content-type marker: white, left-aligned with the text and artwork, on a third
  fixed line below the label area

The content-type marker is the one intentional addition to the golden-master
layout. It makes the likely playback scope apparent before scanning: a disc circle
for an album, three stacked dot-dash rows for a playlist, and a right-pointing play
mark with a short heavy dash for a track. The marks should be drawn as simple
geometry rather than font glyphs so they render consistently. They must remain
small and visually subordinate to the labels, use the same left anchor for every
content type, and occupy the same third-line vertical position even when a
playlist has no secondary label. Exact dimensions, stroke widths, and spacing
should be settled with side-by-side rendered comparisons.

The exact QR module scale, quiet zone, corner radius, font files, font sizes, and
vertical text offsets must be recovered by comparison with the golden masters.
They must not be approximated into a visibly different design. Golden-image and
geometry tests should preserve the recovered values.

All four reference PNGs contain 72-DPI metadata. That metadata does not establish
their intended physical print size, so the existing successful print scaling must
be recorded separately rather than inferred from DPI.

### Width and Text Overflow

The 1200-pixel canvas is the canonical baseline. The Nine Inch Nails reference
shows the practical limitation of the current right-hand width for long titles.

If a wider variant is needed, it may extend only the right edge of the card. The
canvas height, outer margins, QR panel, QR symbol, gap, content-column start, and
vertical layout remain unchanged. The baseline must remain available. The exact
maximum width and whether the artwork expands with the column remain refinement
decisions to be settled with rendered comparisons.

Long text must never cause the QR panel to shrink or move. The eventual overflow
rule may use a wider card, bounded font reduction, or ellipsis, but should remain
deterministic in the downloaded image.

The selection review must show unabridged labels before download so the adult can
identify any text that the deterministic card layout will shorten.

### QR Rules

- Generate a standard QR code, not a Spotify Code.
- Encode only the normalized Spotify URI selected for the card.
- Preserve the reference QR panel size and quiet zone.
- Render modules on an integer pixel grid without antialiasing, blur, decoration,
  embedded logos, or recoloring.
- Keep maximum black-on-white contrast.
- Validate the decoded value before making the card downloadable.
- Test the generated card with the actual presentation scanner, at the established
  print size, and after lamination.

### Artwork Rules

- Keep the artwork region distinct from the QR and text regions.
- Preserve the complete image by default; do not silently crop.
- Never crop or alter Spotify-provided artwork.
- Permit an explicit adult-selected crop only for uploaded or generated original
  artwork.
- Do not upscale a visibly low-resolution image without warning in the selection
  review.

### Output

The required first output is one RGB PNG card matching the golden-master canvas
and layout. A deterministic SVG or other vector intermediate is acceptable if it
helps preserve QR sharpness, but the adult should not need a graphics application
to obtain the final PNG.

From the selection review, the primary action must return that PNG as a download
in one operation. Rendering and QR validation may happen as part of the action,
but the browser must not require the adult to create an intermediate preview and
then click a second download control.

A printer-friendly A4 sheet and PDF export are natural follow-ups after the single
card output and physical scale are validated.

## Product and Policy Boundary

The intended integration is parent-operated and parent-authenticated:

- the adult searches and selects content
- the adult owns and controls the authenticated Spotify account
- the adult curates the available physical card library
- children do not sign in, search Spotify, or receive personalized recommendations
  from the Card Maker
- the child-facing jukebox remains a screenless physical playback interaction used
  under parental supervision

Spotify's current Developer Policy, Developer Terms, and Design Guidelines still
apply to API-derived metadata and artwork. Before distribution beyond the private
household use case, the implementation should re-check the current terms and
resolve attribution and link-back presentation without weakening the locked QR
layout. This concept records the intended operating boundary; it is not a legal
determination.

Relevant current references:

- [Spotify Search API](https://developer.spotify.com/documentation/web-api/reference/search)
- [Spotify URI and ID formats](https://developer.spotify.com/documentation/web-api/concepts/spotify-uris-ids)
- [Spotify Developer Policy](https://developer.spotify.com/policy)
- [Spotify Developer Terms](https://developer.spotify.com/terms)
- [Spotify Design and Branding Guidelines](https://developer.spotify.com/documentation/design)

## Suggested Product Shape

A small browser UI is preferred over the old manifest-driven CLI idea because the
core value is interactive discovery, artwork choice, and visual confirmation.

The implementation should retain narrow internal boundaries:

- `SpotifyCatalog`: search, resolve pasted references, and return normalized
  candidate metadata
- `CoverSource`: represent Spotify, uploaded, and generated image provenance
- `QrEncoder`: produce and verify the exact Spotify URI QR
- `CardRenderer`: compose a deterministic card from a typed draft and locked
  geometry
- browser UI: coordinate search, selection, cover choice, selection review, and
  direct download

The existing lightweight operator HTTP server is a possible host, but the
Card Maker should first prove itself independently. The core catalog, QR, and
rendering logic must remain runnable and testable on a development machine without
Raspberry Pi hardware.

## Quick Spike

The browser spike has been implemented and exercised successfully. Generated
cards appear visually compatible with the previously created cards in side-by-side
PNG comparison. This is useful layout evidence, but it does not replace validation
with the physical scanner, established print scaling, and lamination.

The spike also exposed two UX refinements now incorporated above: downloading
directly from the selection review, and adding a small third-line marker so the
content type is apparent before scanning.

### Question to Answer

Can an adult go from a live Spotify search to a correctly labeled, scannable card
that visibly matches the tested cards, without manual URI or image preparation?

### Timebox

Half a day, with a hard stop after one working day. The spike is for evidence, not
production hardening.

### Spike Scope

Build an isolated local Card Maker spike rather than modifying the appliance
runtime:

1. Serve one plain browser page from a small local Python entrypoint.
2. Read existing Spotify application credentials from environment variables.
3. Search live Spotify catalog results for track, album, and playlist, with a small
   result limit.
4. Allow a Spotify URL or URI to be pasted as an alternative.
5. Select one result and map it to the label fields defined above.
6. Use only Spotify-provided artwork during the spike.
7. Generate a standard QR containing the normalized Spotify URI.
8. Compose a 1200 x 756 PNG using the recovered golden-master geometry.
9. Provide one `Download PNG` action that renders, verifies, and immediately
   downloads the full-resolution card without a separate preview-generation step.

Using Pillow for PNG composition and Segno for QR generation is an acceptable
spike choice. Both should be isolated as Card Maker dependencies so the jukebox
runtime does not acquire them accidentally.

### Explicit Spike Exclusions

- image generation
- uploaded artwork and crop controls
- A4 sheets or PDF generation
- saved card libraries or project persistence
- multiple layouts or themes
- operator-server integration and Pi deployment
- polished Spotify reauthorization UI

### Spike Checks

The spike succeeds only if:

- a live search can select at least one track, one album, and one playlist
- each result produces the correct supported Spotify URI
- track, album, and playlist labels follow the defined metadata mapping
- each supported type renders its specified third-line marker at the shared
  left-aligned anchor
- Unicode text such as German names renders correctly
- the output is exactly 1200 x 756 pixels
- the QR panel and content-column anchors match the golden-master coordinates
- the generated QR decodes to the exact URI before download
- at least one spike card scans from the screen with the actual scanner
- at least one spike card scans after printing and lamination at the established
  physical size
- a side-by-side comparison identifies any remaining font, offset, or artwork-fit
  differences from the golden masters and confirms that the new type markers are
  legible without dominating the label area
- credentials do not appear in browser responses, output files, or logs
- temporary Spotify metadata and artwork are not retained as a local catalog

If live Spotify access is unavailable, fixtures may continue validating the
renderer, but the spike is not considered complete until live search and selection
have been demonstrated.

### Spike Output

The spike should leave behind:

- one short run command
- one generated example for each supported Spotify type
- a captured geometry comparison against the golden masters
- a scanner and print-validation note
- a concise list of API, rendering, and workflow findings that determine the MVP
  technical design

## Refinement Questions

- Where should the production Card Maker run: as part of the Pi operator surface,
  as a separate local tool, or both through the same core package?
- What exact physical print scaling produced the successful existing cards?
- Which font files and exact text offsets reproduce the golden masters?
- What exact dimensions, stroke widths, and spacing make the three type markers
  readable while keeping them subordinate to the labels?
- How much additional width is acceptable, and should artwork grow with it?
- What deterministic fallback handles exceptionally long artist and title text?
- Where should required Spotify attribution and link-back appear while preserving
  the tested front layout?
- Should the first MVP include uploaded artwork, generated artwork, or both?
- Which image-generation provider and credential flow should be supported?
- Should completed card specifications be saved for later re-rendering, or should
  the first version remain session-only?
- When should A4 sheet layout and printer calibration enter scope?
