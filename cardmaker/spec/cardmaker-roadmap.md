# Jukebox Card Maker Roadmap

Status: draft for review

## Purpose and Sizing

This roadmap groups the remaining work between the implemented browser spike and
the complete product described in
[`cardmaker-concept.md`](cardmaker-concept.md).

The existing spike is the starting baseline, not disposable prototype code. Its
catalog, reference normalization, QR verification, renderer, service boundary,
and automated tests are suitable foundations for the remaining work.

The `CM-` prefix keeps these Card Maker epics distinct from the appliance epics in
[`../../spec/roadmap.md`](../../spec/roadmap.md).

## Implemented Baseline

The spike already provides:

- an isolated Flask application and plain browser UI
- Spotify search across tracks, albums, and playlists
- pasted Spotify URL and URI resolution
- normalized Spotify URI payloads and metadata mapping
- server-side client-credentials access with bounded, typed failure handling
- bounded, in-memory Spotify artwork fetching without cropping or persistence
- deterministic 1200 x 756 RGB PNG rendering with packaged fonts
- standard QR generation and independent decode verification before PNG return
- deterministic text fitting and filesystem-safe suggested filenames
- separation from the jukebox playback process and cross-package URI contract tests
- automated lint, type, unit, HTTP, QR, geometry, and golden-fixture checks

The spike has also been exercised successfully in the browser, and its generated
PNGs appear visually compatible beside previously created cards. The remaining
manual scanner, print-scale, and lamination checks are still recorded as incomplete
in [`../findings/spike-validation.md`](../findings/spike-validation.md).

## Gap Inventory

| Area | Spike baseline | Full-concept target | Remaining work | Epic |
| --- | --- | --- | --- | --- |
| Download flow | Explicit `Create preview`, followed by `Download PNG` | One action from selection review renders, verifies, and downloads | Remove the intermediate preview action and preserve errors, filenames, and repeat-card flow | CM-1 |
| Content-type distinction | Type is visible in browser metadata only | Track, album, and playlist cards carry distinct third-line markers | Add the three deterministic geometric markers and visual regression coverage | CM-1 |
| Typography and overflow | Packaged DejaVu fonts with deterministic shrink and ellipsis | A settled, compared layout with predictable overflow | Review the current rule against real long labels and either approve it or replace it with one final documented rule | CM-1 |
| Physical validation | Automated QR and PNG checks pass; manual checklist remains open | Demonstrated live, screen-scanned, printed, laminated cards at a recorded scale | Complete and record the live and physical evidence without inferring scale from DPI | CM-1 |
| Spotify artwork | Implemented with provenance, containment, and no persistence | Fast default cover source | No material product gap | — |
| Adult-provided artwork | Not implemented | Bounded upload with explicit fit/crop and no silent modification | Add the upload source, review controls, validation, provenance, and in-memory render path | CM-2 |
| Generated original artwork | Not implemented | Adult-authored prompt, server-side provider credentials, review, selection, and graceful fallback | Choose one provider and add an isolated provider path without sending Spotify metadata or artwork | CM-2 |
| Product runtime | Development server, loopback default, no Pi unit or deploy flow | Adult-reachable local tool that remains isolated from playback | Settle the host, add a production process/service, deploy it, and validate Pi resource and failure isolation | CM-3 |
| Operator access | Standalone port only | Reachable from the intended operator surface or documented local URL | Add the selected entry point and operational guidance without coupling service lifecycles | CM-3 |
| Attribution and distribution | Spotify attribution and entity link are present in the browser | Applicable attribution/link-back is resolved before use beyond the private household | Recheck and document the boundary when production exposure is selected | CM-3 |

## CM-1: Complete the Spotify-Card MVP

### Objective

Turn the working spike into the smallest complete, physically validated Card Maker
for Spotify-provided artwork.

### Slice 1: Direct Download and Content-Type Markers

- Replace the review screen's `Create preview` action with one primary
  `Download PNG` action.
- Render and verify once, then initiate download immediately using the returned PNG
  and suggested filename.
- Keep selection state and errors usable after success or failure so another card
  can be made without restarting the server.
- Draw the content-type markers as deterministic white geometry at one shared
  third-line anchor:
  - album: disc circle
  - playlist: three stacked dot-dash rows
  - track: right-pointing play mark with a short heavy dash
- Add renderer, golden-fixture, service, HTTP, and browser-shell coverage for the
  new behavior.

### Slice 2: Layout Decisions and Physical Evidence

- Compare the markers, current packaged fonts, text offsets, and representative
  short and long labels beside the golden masters and newly generated cards.
- Settle one deterministic baseline overflow rule. A wider-card variant remains
  optional unless comparison shows it is necessary.
- Update the approved deterministic fixture and geometry documentation after the
  layout is accepted.
- Record one live track, album, and playlist example with normalized URI and
  independent decoder output.
- Complete an actual screen scan and one measured print, laminate, and scan cycle.
- Record the printer, application, scale, paper, orientation, and physical output
  dimensions in the spike findings.

### Completion Gate

- The browser has no preview-generation step or second download control.
- Each supported Spotify type produces its correct, legible marker without moving
  or shrinking the QR panel.
- The final overflow behavior is documented and covered by deterministic tests.
- All automated checks pass.
- The live Spotify, scanner, print-scale, and lamination evidence required by the
  concept is recorded.

### Deferred from CM-1

- uploaded and generated artwork
- Pi deployment
- batch, ZIP, A4, and PDF output
- saved card projects or a card library

## CM-2: Complete the Cover-Source Model

### Objective

Support all three cover sources in the concept while preserving explicit
provenance, adult control, bounded in-memory processing, and the locked card
layout.

### Slice 1: Adult-Provided Artwork

- Extend the draft model from a Spotify-only discriminator to an explicit cover
  source model without weakening the existing Spotify path.
- Accept supported raster uploads with bounded size, safe decoding, and clear
  errors; do not create a server-side artwork archive.
- Show a fit review and allow an explicit adult-selected crop for uploaded artwork.
- Preserve the original upload for the duration of the browser session and never
  crop or otherwise modify it silently.
- Render the reviewed upload through the same verified QR and PNG pipeline.
- Cover upload validation, provenance, fit/crop behavior, and Spotify no-crop
  regression in automated tests.

### Slice 2: Generated Original Artwork

- Select one image-generation provider and define its server-side credential
  configuration before technical implementation begins.
- Add a narrow provider adapter so generation is optional and does not affect
  Spotify discovery or ordinary rendering when unavailable.
- Accept only an adult-authored, visibly editable prompt. Do not automatically
  send Spotify metadata or Spotify artwork to the provider.
- Let the adult review and select a generated result before using it on a card.
- Apply the same explicit fit/crop rules allowed for other original artwork.
- Keep provider failures honest and preserve Spotify artwork and upload as usable
  alternatives.
- Test the application contract with a deterministic provider test adapter; do not
  represent fixtures as live generation success.

### Completion Gate

- Spotify, uploaded, and generated covers are visibly identified and follow their
  distinct modification rules.
- Spotify artwork still cannot be cropped or altered.
- Uploaded and generated images are reviewed before download and remain
  session-only unless a later persistence decision changes the concept.
- Provider and Spotify credentials never reach browser responses, PNG metadata, or
  logs.
- A failure in one optional cover source does not block the others.

### Deferred from CM-2

- automatic prompts derived from Spotify data
- background generation, recommendations, or child-facing generation
- persistent uploads, generated-image history, and saved card projects
- multiple themes or a free-form design editor

## CM-3: Productionize the Local Operator Tool

### Objective

Make the complete Card Maker routinely available to the adult operator without
coupling its availability or failure modes to jukebox playback.

### Decision Gate

Before detailed requirements are written, confirm the production host. The current
technical direction recommends a separate Card Maker service on the Raspberry Pi,
reachable on the local network and optionally linked from the existing operator
surface. A development-machine-only product would remove most of Slice 1 but would
need to be chosen explicitly in the concept.

### Slice 1: Production Process and Deployment

- Replace the Werkzeug development-server launch path with a lightweight supported
  WSGI process suitable for the selected host and Raspberry Pi 3 constraints.
- For the recommended Pi path, add a separate Card Maker virtualenv, environment
  file, `systemd` unit, and deploy/bootstrap handling.
- Keep Card Maker credentials and lifecycle separate from jukebox playback state
  and secrets.
- Confirm required Python packages, including independent QR decoding, install and
  run on the actual Pi OS architecture.
- Ensure Card Maker startup, restart, upgrade, or failure cannot stop or restart
  the jukebox service.

### Slice 2: Operator Entry Point and Operational Validation

- Expose the selected local URL and, for the Pi path, add a simple link from the
  existing operator surface without introducing service-to-service calls.
- Document setup, credentials, health checking, logs, restart, upgrade, and common
  Spotify/API failures.
- Validate boot availability, LAN access, rendering, memory use, and acceptable
  responsiveness on the Raspberry Pi 3.
- Validate failure isolation while scan-to-playback continues normally.
- Recheck Spotify attribution and link-back presentation for the chosen private
  household deployment boundary.
- Keep public hosting out of scope unless TLS, access control, and operational
  limits are separately specified.

### Completion Gate

- The adult can reach the Card Maker through the documented operator path after a
  clean boot.
- The production service can create and download cards on the selected host within
  Raspberry Pi 3 constraints.
- Playback remains available while Card Maker is stopped, restarted, or failed.
- Secrets remain environment-configured and absent from the repository and browser.
- Deployment, validation, and troubleshooting steps are reproducible.

### Deferred from CM-3

- public Internet hosting
- Card Maker accounts or child profiles
- coupling Card Maker health to jukebox readiness
- analytics, catalogs, recent-card history, or background polling

## Sequencing

1. Complete CM-1 first. It closes the currently observed UX gaps and establishes
   the final card and physical-validation baseline used by every cover source.
2. Complete CM-2 after CM-1 so upload and generation reuse the accepted renderer,
   type markers, and direct-download path.
3. CM-3 may start after CM-1 once the host decision is confirmed. It should deploy
   whichever CM-2 features are complete without coupling their implementation to
   the appliance runtime.

CM-1 is the release gate for a trustworthy Spotify-artwork MVP. CM-2 closes the
feature gap to the concept's complete three-source authoring flow. CM-3 closes the
operational gap to a routinely available local product.

## Work Not Required to Close the Current Concept

The following ideas remain useful follow-ups, but the concept does not currently
make them completion requirements:

- A4 or PDF sheet layout and printer calibration tooling
- batch queues, ZIP export, or a 100-card workflow
- saved card specifications, projects, or a permanent card library
- a wider canvas when the accepted deterministic overflow rule is sufficient
- search pagination beyond the small initial result set
- hosted/public deployment
- themes or free-form layout editing

Promoting any of these items should be an explicit concept decision followed by a
separate epic, not an incidental addition to CM-1 through CM-3.
