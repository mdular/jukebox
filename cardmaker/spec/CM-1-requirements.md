# CM-1 Requirements Specification

## Title

CM-1: Complete the Spotify-Card MVP

## Purpose

This document defines the requirements for CM-1 from
[`cardmaker-roadmap.md`](cardmaker-roadmap.md). It turns the implemented browser
spike into the smallest complete Card Maker for Spotify-provided artwork.

This is a requirements document, not a technical design. It defines the direct
download workflow, content-type distinction, final layout approval, and live and
physical evidence required before the Spotify-artwork MVP can be treated as
complete.

The implemented behavior and open evidence recorded in
[`../findings/spike-validation.md`](../findings/spike-validation.md) are the CM-1
starting point. Checked decisions below are already fixed by
[`cardmaker-concept.md`](cardmaker-concept.md) or the roadmap; unchecked decisions
still require review.

## Objective

Deliver a trustworthy one-card-at-a-time workflow in which an adult can select a
Spotify track, album, or playlist, review its complete metadata and artwork, and
use one action to download a verified, visibly type-specific card that has been
validated through the real print, laminate, and scan workflow.

## Success Definition

CM-1 is complete when all of the following are true:

- The selection review offers one primary `Download PNG` action and no separate
  preview-generation or second download step.
- Track, album, and playlist cards use their specified geometric markers at the
  same third-line anchor without changing the locked QR geometry.
- One deterministic text-overflow and typography rule has been selected,
  documented, and covered by stable visual and geometry checks.
- The downloaded image is the same image that was rendered and independently QR
  verified for the selected normalized Spotify URI.
- Live Spotify examples for all three supported content types and the required
  screen, print, laminate, and scanner evidence are recorded.
- Existing Spotify-artwork provenance, no-crop behavior, secret handling, and
  in-memory processing continue to pass regression checks.

## Decision Checklist

Use this section to settle the remaining CM-1 product decisions. Checked items are
already selected by the concept and roadmap. Open alternatives remain unchecked,
and the preferred default is marked `(Recommended)`.

### D-1 Download Interaction

The concept replaces the spike's two-step preview and download interaction with
one action from the selection review.

- [x] Render, verify, and immediately download through one primary `Download PNG`
  action. (Recommended)
- [ ] Keep a separate `Create preview` action followed by a download action.
- [ ] Download without showing the selected URI, labels, artwork, and content type
  first.

### D-2 Content-Type Marker Set

The card must reveal likely playback scope without relying on extra text or
changing the established label and QR regions.

- [x] Use a disc circle for albums, three stacked dot-dash rows for playlists, and
  a right-pointing play mark with a short heavy dash for tracks. (Recommended)
- [ ] Use text labels for the three content types.
- [ ] Omit content-type distinction from the downloaded card.

### D-3 Text Overflow and Card Width

The spike currently keeps the 1200-pixel canvas, reduces text by deterministic
steps to a lower bound, and then applies an ellipsis. CM-1 must approve that rule
or select one of the alternatives already allowed by the concept.

- [x] Keep the 1200 x 756 baseline and approve the current bounded
  shrink-then-ellipsis rule. (Recommended)
- [ ] Keep the 1200 x 756 baseline and use a deterministic ellipsis rule without
  bounded font reduction.
- [ ] Add a variant that extends only the right edge while preserving the baseline
  card and all locked QR and vertical geometry.

### D-4 Typography and Vertical Layout Approval

The packaged fonts and current offsets are deterministic and appear visually
compatible with the golden masters, but the roadmap still requires explicit
comparison and approval.

- [x] Approve the current packaged fonts and offsets after side-by-side review
  confirms legibility and acceptable visual compatibility. (Recommended)
- [ ] Replace one or both fonts or adjust the text offsets, then approve and lock
  the revised baseline through the same comparison.

User note: The comparison has already happened. Current font is confirmed and approved.

### D-5 Physical Release Gate

Automated QR and image checks do not replace evidence from the actual scanner and
physical card workflow.

- [x] Require all live Spotify, screen-scan, measured print, lamination, and final
  scanner evidence before CM-1 completes. (Recommended)
- [ ] Treat automated and fixture-based checks as sufficient for CM-1 completion.
- [ ] Defer physical validation until after additional cover sources are added.

## In Scope

- Replacing the spike's intermediate preview action with direct verified download
  from the selection review.
- Keeping the adult's current selection and error context usable after a successful
  or failed download attempt.
- Adding the fixed album, playlist, and track marker meanings from the concept.
- Settling marker proportions and spacing through side-by-side visual review while
  preserving their shared anchor and subordinate visual role.
- Selecting and documenting one deterministic text-overflow and typography
  baseline.
- Updating the approved deterministic fixture and geometry evidence only after the
  final layout is accepted.
- Recording live Spotify and independent QR-decode evidence for a track, album, and
  playlist.
- Completing and recording one actual on-screen scanner check and one measured
  print, laminate, and scanner cycle.
- Regressing the existing Spotify-only discovery, provenance, rendering, security,
  and no-persistence behavior.

## Out of Scope

- Uploaded artwork, generated artwork, or any additional cover source.
- Raspberry Pi production deployment or operator-surface integration.
- A4 or PDF sheets, batch queues, ZIP output, or printer-calibration tooling.
- Saved cards, projects, search history, or a persistent card library.
- Themes, a free-form layout editor, or changes to the locked QR payload contract.
- Public hosting, accounts, child profiles, playback controls, or Spotify library
  management.

## Functional Requirements

### FR-1 Selection Review

The Card Maker shall show the adult the complete selection before download.

Requirements:

- The review shall show the exact normalized Spotify URI.
- The review shall show the unabridged primary and secondary labels supplied by the
  selected Spotify item, including labels that the final card may shorten.
- The review shall show the selected Spotify artwork and the content type.
- The review shall retain Spotify attribution and a link to the selected Spotify
  entity.
- The review shall make `Download PNG` the single primary card-production action.

Related decision: `D-1 Download Interaction`.

### FR-2 Direct Verified Download

One adult action shall compose, verify, and download the selected card.

Requirements:

- Activating `Download PNG` shall render the full-resolution card and independently
  decode its QR before the browser starts the download.
- The QR decode shall exactly equal the normalized Spotify URI shown in the
  selection review.
- The downloaded PNG shall be the same verified render produced by that action;
  the application shall not perform an unreviewed second render for download.
- A render or QR-verification failure shall prevent download and present an honest,
  usable error on the current selection.
- The browser shall not require a separate `Create preview` action or expose a
  second download control.

Related decision: `D-1 Download Interaction`.

### FR-3 Repeat-Card Flow

The adult shall be able to recover from an error or begin another card without
restarting the Card Maker.

Requirements:

- A successful download shall leave a clear path to make another card.
- A failed download shall preserve enough of the current selection to understand
  the failure and retry or choose another item.
- Resetting for another card shall release the prior downloaded-image state without
  requiring a server restart.
- Search, pasted-reference, and selection behavior from the spike shall remain
  available after a prior success or failure.

### FR-4 Content-Type Markers

Each downloaded card shall carry the marker assigned to its Spotify content type.

Requirements:

- An album card shall show a disc-circle marker.
- A playlist card shall show three stacked dot-dash rows.
- A track card shall show a right-pointing play mark with a short heavy dash.
- The markers shall be white deterministic geometry rather than font glyphs.
- Every marker shall use the same left anchor and third-line vertical position.
- A playlist marker shall occupy that third-line position even though a playlist
  has no secondary label.
- The marker shall remain visually subordinate to the artwork and labels and shall
  not overlap them.

Related decision: `D-2 Content-Type Marker Set`.

### FR-5 Locked Card Geometry

CM-1 shall preserve the tested card and QR geometry while adding the marker and
settling text behavior.

Requirements:

- The canonical card shall remain a 1200 x 756 RGB PNG with a solid black
  background.
- The outer margin, 676 x 676 QR panel at `(40, 40)`, 40-pixel gap, and content
  column beginning at `x = 756` shall remain unchanged.
- Long labels and markers shall never shrink, move, cover, or reduce the QR panel.
- Artwork shall remain top-aligned in the content column with aspect ratio
  preserved.
- Spotify-provided artwork shall remain uncropped, undistorted, and unaltered.
- If D-3 selects a wider variant, only the right edge may move; the 1200-pixel
  baseline and all locked left-side and vertical geometry shall remain available.

Related decisions: `D-2 Content-Type Marker Set` and `D-3 Text Overflow and Card
Width`.

### FR-6 Deterministic Label Rendering

The final card shall apply one predictable rule to labels that do not fit the
available content width.

Requirements:

- Identical card inputs shall produce identical label placement and overflow
  behavior.
- The accepted rule shall define bounded behavior for exceptionally long artist,
  track, album, and playlist labels.
- Any reduction or truncation in the downloaded card shall not alter the full
  metadata shown in the selection review.
- Multiple artist names and Unicode text shall retain Spotify's supplied spelling
  and order.
- The selected font files, starting sizes, lower bounds, offsets, and overflow
  behavior shall be recorded with the approved layout evidence.

Related decisions: `D-3 Text Overflow and Card Width` and `D-4 Typography and
Vertical Layout Approval`.

### FR-7 Spotify Payload and Artwork Integrity

The CM-1 changes shall preserve the trusted Spotify-only card contract established
by the spike.

Requirements:

- The QR shall contain only the normalized Spotify URI for the selected track,
  album, or playlist.
- Tracking parameters from pasted Spotify URLs shall not appear in the QR payload.
- Labels and artwork used for rendering shall remain associated with the selected
  Spotify entity.
- Spotify artwork shall be contained without cropping, distortion, filters,
  overlays, recoloring, or generated extension.
- A card shall not be returned when its composed QR cannot be decoded exactly.

### FR-8 Live and Physical Validation Record

CM-1 shall close the manual evidence gap documented by the spike.

Requirements:

- The validation record shall include one live selected track, one live selected
  album, and one live selected playlist with their full labels and normalized URIs.
- The independent decoder output shall be recorded for all three live examples.
- One generated example of each supported type shall be retained for review.
- At least one full-resolution card shall be scanned from a screen with the actual
  presentation scanner.
- At least one card shall be printed at a measured scale, laminated, and scanned
  with the actual presentation scanner.
- The physical record shall identify the printer, printing application, scale
  setting, paper, orientation, and measured output dimensions.
- Physical scale shall be measured and shall not be inferred from PNG DPI metadata.

Related decision: `D-5 Physical Release Gate`.

## Non-Functional Requirements

### NFR-1 Determinism and Regression Safety

- Repeated rendering of the same controlled input shall produce the approved
  geometry, marker, label, artwork, and QR result.
- Automated checks shall cover each marker type, the selected overflow behavior,
  direct-download HTTP behavior, independent QR verification, and the locked layout
  anchors.
- The approved deterministic fixture shall change only as part of the reviewed
  CM-1 layout approval.
- Existing search, URL and URI normalization, metadata mapping, error handling,
  and jukebox URI-contract checks shall continue to pass.

### NFR-2 Adult Usability

- The ordinary workflow shall keep one clear primary action at each step.
- The download action shall not make the adult repeat discovery or selection.
- Errors shall remain specific enough for the adult to retry, change the selection,
  or return to discovery.
- The type marker and final label treatment shall remain legible without competing
  with the artwork or QR.

### NFR-3 Security, Privacy, and Retention

- Spotify credentials and access tokens shall remain server-side and absent from
  browser responses, PNG metadata, and logs.
- Card and artwork responses shall remain non-cacheable by the server interface.
- Spotify metadata, artwork, and rendered cards shall not become a persistent
  server-side catalog or archive.
- CM-1 shall add no background Spotify polling or automatic retries.

### NFR-4 Runtime Compatibility

- The Card Maker shall remain isolated from the jukebox playback package and
  process.
- CM-1 shall remain runnable and testable on a non-Pi development machine.
- The changes shall not add a runtime dependency to the jukebox distribution.

## Acceptance Criteria

### AC-1 One-Step Download

- Given an adult has selected and reviewed a supported Spotify item
- When they activate `Download PNG`
- Then the application renders and independently verifies one full-resolution card
- And the browser immediately starts downloading that verified PNG
- And no separate preview-generation or second download action is required.

### AC-2 Verification Failure

- Given the composed card's QR cannot be decoded to the exact selected normalized
  Spotify URI
- When the adult activates `Download PNG`
- Then no PNG download begins
- And the current selection remains visible with an honest verification error.

### AC-3 Track Marker

- Given a selected Spotify track
- When its card is downloaded
- Then the card shows the right-pointing play mark with a short heavy dash at the
  shared third-line anchor
- And the QR panel and label anchors remain unchanged.

### AC-4 Album Marker

- Given a selected Spotify album
- When its card is downloaded
- Then the card shows the disc-circle marker at the shared third-line anchor
- And the QR panel and label anchors remain unchanged.

### AC-5 Playlist Marker

- Given a selected Spotify playlist with no secondary label
- When its card is downloaded
- Then the card shows three stacked dot-dash rows at the same third-line anchor used
  by track and album cards
- And no secondary text is invented.

### AC-6 Long Label

- Given a selected item whose full label exceeds the accepted content width
- When its card is downloaded
- Then the card applies the approved deterministic overflow rule
- And the QR panel does not move or shrink
- And the unabridged label remains visible in the selection review.

### AC-7 Repeat After Success

- Given a card download has completed
- When the adult chooses to make another card
- Then discovery and selection remain usable without restarting the server
- And the previous rendered-image state is released.

### AC-8 Retry After Failure

- Given rendering, Spotify access, artwork fetching, or QR verification fails
- When the error is shown
- Then the adult can retry or select another item without restarting the server
- And the failed attempt does not leave a partial server-side output file.

### AC-9 Live Type Coverage

- Given live Spotify access is configured
- When one track, one album, and one playlist are selected and downloaded
- Then each card contains the normalized URI and metadata mapping for its selected
  entity
- And the independent decoder output and example PNG are recorded for all three.

### AC-10 Screen Scanner Evidence

- Given a full-resolution CM-1 card is displayed on a screen
- When it is presented to the actual scanner
- Then the scanner reads the exact normalized Spotify URI
- And the result is recorded in the validation findings.

### AC-11 Printed and Laminated Evidence

- Given a CM-1 card has been printed using recorded settings and laminated
- When it is presented to the actual scanner
- Then the scanner reads the exact normalized Spotify URI
- And the printer, application, scale, paper, orientation, and measured physical
  dimensions are recorded.

### AC-12 Automated Regression Gate

- Given the final CM-1 layout and workflow have been approved
- When the Card Maker automated checks run
- Then direct download, all three markers, the accepted overflow rule, exact QR
  verification, locked geometry, Spotify no-crop behavior, and existing discovery
  behavior pass.

## Deliverables

- A selection-review flow with one direct, verified `Download PNG` action.
- Deterministic album, playlist, and track markers in the locked card layout.
- A selected and documented typography, offset, overflow, and width baseline.
- Updated automated behavior, geometry, and approved-fixture coverage.
- One recorded live example and independent decoder result for each supported
  Spotify type.
- A completed screen-scan and measured print, laminate, and scan record in the
  spike findings.

## CM-2 Handoff Questions

- Which option is selected for `D-3 Text Overflow and Card Width`?
- Which font and offset baseline is approved under `D-4 Typography and Vertical
  Layout Approval`?
- What final marker dimensions and spacing passed the side-by-side review?
- Are every live and physical evidence item in `FR-8` and `AC-9` through `AC-11`
  recorded and reproducible?
- Is the accepted layout fixture ready to become the shared output baseline for
  uploaded and generated cover sources?

## Notes

- CM-1 is the release gate for the Spotify-artwork MVP and should complete before
  CM-2 changes the cover-source model.
- The current deterministic shrink-and-ellipsis behavior is a recommendation, not
  a selected final requirement until `D-3` is checked.
- This document intentionally does not define implementation modules, HTTP payload
  shapes, marker drawing coordinates, or deployment details. Those belong in a
  separate CM-1 technical design after the open decisions are taken.
