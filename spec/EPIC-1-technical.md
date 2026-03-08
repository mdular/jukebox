# EPIC 1 Technical Design

## Purpose

This document turns [EPIC-1.md](/Users/markus/Workspace/jukebox/spec/EPIC-1.md) into an implementation design for the current Python repository.
It is intentionally scoped to EPIC 1: local validation of the scan-to-playback control loop.

This design is grounded in the current repo state:

- Python 3.11 package scaffold under `src/jukebox`
- `python -m jukebox` as the canonical entrypoint
- existing config and logging modules
- local workflow wrappers in `scripts/`
- automated checks via `make check`

## Selected Decisions Carried Into This Design

This technical design assumes the checked decisions in [EPIC-1.md](/Users/markus/Workspace/jukebox/spec/EPIC-1.md):

- Emulated input and real USB scanner validation both matter in EPIC 1.
- Accepted payloads are strict Spotify URIs only.
- Supported URI types are `track`, `album`, and `playlist`.
- Playback validation uses a stub backend by default with an optional real Spotify trigger backend.
- Duplicate suppression uses an exact payload match and a 2 second window.
- New valid scans replace the prior playback intent.
- Feedback is terminal status plus structured logs.
- Recoverable errors do not terminate the controller loop.
- The local workflow stays lightweight and testable within the current Python project.

## Design Goals

- Reuse the existing scaffold rather than introduce a parallel application shape.
- Keep the core controller logic pure and easy to unit test.
- Use the same scan ingestion path for both manual input and a keyboard-wedge USB scanner.
- Keep runtime dependencies at zero for EPIC 1 unless implementation proves that unrealistic.
- Preserve a clear adapter boundary so EPIC 2 can swap in Raspberry Pi specific input and playback integrations.

## Non-Goals

- No Raspberry Pi deployment work.
- No GPIO, LED wiring, or button integration.
- No local media fallback.
- No queueing or richer playback control.
- No GUI or web interface.

## Current Baseline

The repository already provides the following useful pieces:

- [main.py](/Users/markus/Workspace/jukebox/src/jukebox/main.py) loads config, configures logging, and exits cleanly.
- [config.py](/Users/markus/Workspace/jukebox/src/jukebox/config.py) already validates environment-driven settings.
- [logging.py](/Users/markus/Workspace/jukebox/src/jukebox/logging.py) already supports console and JSON log formats.
- [run-local.sh](/Users/markus/Workspace/jukebox/scripts/run-local.sh) already sources `.env` and runs `python -m jukebox`.
- The test suite already uses `pytest` as a runner with `unittest`-style test modules.

EPIC 1 should extend those pieces instead of replacing them.

## Key Design Choice: Shared `stdin` Scan Path

EPIC 1 will use line-oriented `stdin` input as the single scan source.

This satisfies both selected scan modes:

- Emulated input: a developer types or pipes newline-terminated payloads into the process.
- Real USB scanner input: the scanner runs in keyboard mode and "types" into the focused terminal, ending each scan with newline.

This is the lowest-risk cross-platform approach for local validation and avoids premature HID-device work in EPIC 1.
It also means the controller logic does not care whether a line came from a person or a scanner.

## Spec Alignment Note

There is one requirements tension worth resolving explicitly.

The selected note under D-7 says "If it's the same as the current playback, do nothing."
However, AC-5 in [EPIC-1.md](/Users/markus/Workspace/jukebox/spec/EPIC-1.md) says that the same payload scanned again after the duplicate window expires should trigger playback again.

For EPIC 1, this design follows the acceptance criteria:

- the same payload is suppressed only within the 2 second duplicate window
- after that window, the same payload is treated as a fresh valid scan

Reason: EPIC 1 does not need to query live playback state to prove the controller loop, and adding "already playing" introspection would complicate the design for limited value at this stage.

## Proposed Architecture

```text
stdin
  -> ScanLineReader
  -> Controller
       -> SpotifyUriParser
       -> DuplicateGate
       -> PlaybackBackend
            -> StubPlaybackBackend
            -> SpotifyPlaybackBackend
       -> FeedbackSink
            -> TerminalStatusSink
       -> EventLogger
  -> process exit on EOF or unrecoverable startup/config error
```

The controller owns the decision flow.
Adapters handle side effects.
Parsing and duplicate suppression remain pure logic modules.

## Runtime Flow

### Startup

1. `python -m jukebox` calls `main()`.
2. `main()` loads settings from environment.
3. `main()` configures logging.
4. `main()` constructs the selected playback backend.
5. `main()` constructs the controller and begins reading `stdin`.
6. The process emits an initial `idle` status and waits for newline-terminated input.

### Per-Scan Handling

1. Read one raw line from `stdin`.
2. Trim trailing `\r` and `\n`.
3. If the result is empty, ignore it and keep reading.
4. Emit a `scan_received` event.
5. Parse the payload as a strict Spotify URI.
6. If invalid, emit `invalid_payload` with a reason code and continue.
7. If the type is well-formed but unsupported, emit `unsupported_content` and continue.
8. Check duplicate suppression against the last successfully dispatched payload.
9. If duplicate within 2 seconds, emit `duplicate_suppressed` and continue.
10. Build a `PlaybackRequest`.
11. Dispatch to the selected playback backend.
12. If dispatch succeeds, record the payload and current monotonic timestamp in the duplicate gate.
13. Emit `playback_dispatch_succeeded`.
14. If dispatch fails, emit `playback_dispatch_failed` with backend and reason details.
15. Do not update the duplicate gate after a failed dispatch so the same scan can be retried immediately.

### Shutdown

- EOF on `stdin` exits cleanly with status code `0`.
- `KeyboardInterrupt` exits cleanly with status code `130`.
- Invalid startup configuration exits with status code `2`, consistent with the existing scaffold.

## Module Plan

The implementation should fit the current package layout and add focused modules rather than one large script.

### Existing Files to Extend

- [main.py](/Users/markus/Workspace/jukebox/src/jukebox/main.py)
  Purpose: app assembly, startup logging, top-level exception handling, long-running loop entrypoint.
- [config.py](/Users/markus/Workspace/jukebox/src/jukebox/config.py)
  Purpose: validate new EPIC 1 runtime settings.
- [logging.py](/Users/markus/Workspace/jukebox/src/jukebox/logging.py)
  Purpose: preserve structured event fields in JSON mode and keep readable console logs.

### New Core Modules

- `src/jukebox/core/models.py`
  Purpose: shared dataclasses and enums for parsed URIs, playback requests, backend results, and controller events.
- `src/jukebox/core/parser.py`
  Purpose: strict Spotify URI parsing and validation.
- `src/jukebox/core/deduper.py`
  Purpose: duplicate suppression using an injected monotonic clock.
- `src/jukebox/core/controller.py`
  Purpose: pure orchestration for one scan at a time.

### New Adapter Modules

- `src/jukebox/adapters/input.py`
  Purpose: line-based scan reader over `TextIO`, with `stdin` as the EPIC 1 implementation.
- `src/jukebox/adapters/playback_stub.py`
  Purpose: fallback backend for tests and local development without Spotify credentials.
- `src/jukebox/adapters/playback_spotify.py`
  Purpose: optional real playback backend using Spotify's player APIs.
- `src/jukebox/adapters/feedback.py`
  Purpose: terminal status rendering to stdout.

This keeps the `core` package domain-oriented and the `adapters` package side-effect-oriented.

## Data Model

### Parsed URI

```python
@dataclass(frozen=True)
class SpotifyUri:
    raw: str
    kind: Literal["track", "album", "playlist"]
    spotify_id: str
```

### Playback Request

```python
@dataclass(frozen=True)
class PlaybackRequest:
    uri: SpotifyUri
```

### Playback Result

```python
@dataclass(frozen=True)
class PlaybackResult:
    ok: bool
    backend: str
    reason_code: str | None = None
    message: str | None = None
```

### Controller Event

```python
@dataclass(frozen=True)
class ControllerEvent:
    code: str
    message: str
    payload: str | None = None
    uri_kind: str | None = None
    backend: str | None = None
    reason_code: str | None = None
```

EPIC 1 does not need a more complicated event bus.
One event object per outcome is sufficient for both status output and logs.

## Parsing Design

The parser will accept only these forms:

- `spotify:track:<id>`
- `spotify:album:<id>`
- `spotify:playlist:<id>`

Implementation rule:

- use a single strict regex or equivalent split-based validator
- require exactly three colon-separated segments
- require the type to be one of `track`, `album`, or `playlist`
- require the Spotify ID to match the expected base62 identifier shape

Proposed validation pattern:

```python
^spotify:(track|album|playlist):([A-Za-z0-9]{22})$
```

If implementation experience shows that Spotify IDs in the selected content types are valid but not always length 22 in practice, the parser may be relaxed to `([A-Za-z0-9]+)`.
The initial implementation should start strict because the requirements selected the strict URI path.

## Duplicate Suppression Design

`DuplicateGate` will store:

- `last_payload: str | None`
- `last_success_monotonic: float | None`
- configured window: `2.0` seconds

Algorithm:

- compare only against the last successfully dispatched payload
- use `time.monotonic()` rather than wall clock time
- suppress only when payload matches exactly after newline trimming and the elapsed time is less than or equal to the configured window
- allow identical payloads immediately after a failed dispatch because no success timestamp is recorded

This matches the selected exact-match rule and improves retry behavior for transient playback failures.

## Playback Backend Design

The controller will depend on a narrow backend interface:

```python
class PlaybackBackend(Protocol):
    def dispatch(self, request: PlaybackRequest) -> PlaybackResult:
        ...
```

### Stub Backend

`StubPlaybackBackend` is the default backend in EPIC 1.

Behavior:

- always returns success
- emits enough detail to show what would have been played
- is used by default in tests and local development

This keeps the local loop usable on any machine with no Spotify setup.

### Spotify Backend

`SpotifyPlaybackBackend` is optional and only enabled when explicitly selected in configuration.

Behavior:

- uses environment-supplied Spotify credentials
- refreshes an access token at runtime
- targets a configured device when one is provided
- dispatches track URIs as a direct track play request
- dispatches album and playlist URIs as a context play request
- maps HTTP/API failures into reason codes the controller can log and surface

Planned configuration:

- `JUKEBOX_PLAYBACK_BACKEND=spotify`
- `JUKEBOX_SPOTIFY_CLIENT_ID`
- `JUKEBOX_SPOTIFY_CLIENT_SECRET`
- `JUKEBOX_SPOTIFY_REFRESH_TOKEN`
- `JUKEBOX_SPOTIFY_DEVICE_ID` optional but recommended for deterministic testing

Failure categories to surface:

- `spotify_auth_error`
- `spotify_no_active_device`
- `spotify_forbidden`
- `spotify_rate_limited`
- `spotify_transport_error`
- `spotify_unexpected_response`

EPIC 1 should implement the Spotify backend with the standard library HTTP stack unless a concrete need for a third-party client appears during implementation.

## Feedback and Logging Design

EPIC 1 needs two outputs:

- human-readable terminal feedback for a developer standing at the terminal
- structured logs for debugging and machine-readable traces

### Terminal Status Sink

`TerminalStatusSink` writes one concise line per major event to stdout.

Example shapes:

```text
[IDLE] waiting for scan input
[SCAN] spotify:track:6rqhFgbbKwnb9MLmUQDhG6
[ACCEPTED] track spotify:track:6rqhFgbbKwnb9MLmUQDhG6
[DUPLICATE] ignored within 2.0s
[ERROR invalid_uri] expected spotify:(track|album|playlist):<id>
[PLAYBACK stub] dispatched track
[PLAYBACK spotify] failed: spotify_no_active_device
```

### Structured Logging

The existing JSON formatter should be extended so log records can include event fields beyond message text.

Recommended approach:

- use a dedicated logger such as `jukebox.event`
- emit controller events with `extra={...}` fields
- include common fields in JSON mode:
  - `event`
  - `payload`
  - `uri_kind`
  - `backend`
  - `reason_code`
  - `environment`
  - `timestamp`
  - `level`
  - `logger`

Console logging can stay human-readable and does not need to expose every field inline.

## Configuration Design

The configuration surface should stay small.

### Existing Variables to Preserve

- `JUKEBOX_ENV`
- `JUKEBOX_LOG_LEVEL`
- `JUKEBOX_LOG_FORMAT`

### New Variables for EPIC 1

- `JUKEBOX_PLAYBACK_BACKEND`
  Allowed values: `stub`, `spotify`
  Default: `stub`
- `JUKEBOX_DUPLICATE_WINDOW_SECONDS`
  Default: `2.0`
  Validation: positive float
- `JUKEBOX_SPOTIFY_CLIENT_ID`
  Required when backend is `spotify`
- `JUKEBOX_SPOTIFY_CLIENT_SECRET`
  Required when backend is `spotify`
- `JUKEBOX_SPOTIFY_REFRESH_TOKEN`
  Required when backend is `spotify`
- `JUKEBOX_SPOTIFY_DEVICE_ID`
  Optional

Configuration should fail fast at startup when the Spotify backend is selected but required credentials are missing.

EPIC 1 does not need a separate scan-source setting because both selected scan modes use the same `stdin` implementation.

## Entry Point Design

[main.py](/Users/markus/Workspace/jukebox/src/jukebox/main.py) should become thin app assembly code.

Responsibilities:

- load settings
- configure logging
- create the selected playback backend
- create terminal feedback sink
- create controller
- iterate over `stdin`
- convert top-level exceptions into stable exit codes

The controller itself should not open files, parse environment variables, or know about process exit codes.

## Testing Strategy

The repo already uses `pytest` plus `unittest`.
EPIC 1 should keep that style.

### New Test Modules

- `tests/test_parser.py`
  Cover valid track, album, and playlist URIs plus malformed and unsupported cases.
- `tests/test_deduper.py`
  Cover within-window suppression, after-window acceptance, and failure-to-record behavior.
- `tests/test_controller.py`
  Cover happy path, invalid payloads, duplicates, backend failures, and successive different scans.
- `tests/test_playback_stub.py`
  Cover stub dispatch output.
- `tests/test_playback_spotify.py`
  Cover request shaping and API error mapping with HTTP mocked.

### Existing Tests to Update

- [test_main.py](/Users/markus/Workspace/jukebox/tests/test_main.py)
  Update the smoke test to assert clean startup and clean exit on EOF rather than immediate scaffold termination.
- [test_config.py](/Users/markus/Workspace/jukebox/tests/test_config.py)
  Extend coverage for new environment variables and validation rules.
- [test_logging.py](/Users/markus/Workspace/jukebox/tests/test_logging.py)
  Extend JSON log assertions to include controller event metadata.

### Manual Replay Inputs

Representative scan streams should live under `tests/fixtures/scan_streams/`.
That allows the same inputs to be reused for both automated tests and manual local validation.

Example manual runs:

```sh
printf '%s\n' 'spotify:track:6rqhFgbbKwnb9MLmUQDhG6' | ./scripts/run-local.sh
./scripts/run-local.sh < tests/fixtures/scan_streams/happy_path.txt
JUKEBOX_PLAYBACK_BACKEND=spotify ./scripts/run-local.sh
```

## Performance Expectations

EPIC 1 does not need formal benchmarking infrastructure.
It does need the code path to stay short and synchronous.

Design implications:

- parsing is constant time
- duplicate suppression is constant time
- status output happens immediately in-process
- only the optional Spotify backend performs network I/O
- the stub backend remains effectively instantaneous

If the Spotify backend makes responsiveness visibly worse, the terminal status sink should emit `scan_received` before the dispatch call so the operator still sees immediate acknowledgement.

## Failure Handling

Recoverable issues remain in-band controller events.

Examples:

- malformed payload
- unsupported URI type
- duplicate suppression
- Spotify auth error
- Spotify device not available
- Spotify API timeout or 5xx response

Unrecoverable issues are limited to:

- invalid startup configuration
- construction failure of the selected backend
- truly unexpected exceptions escaping `main()`

The implementation should keep unexpected exceptions obvious rather than suppressing them silently.

## Implementation Sequence

1. Extend `Settings` and configuration validation for duplicate window and playback backend selection.
2. Add core models, parser, and duplicate gate with unit tests.
3. Add terminal feedback sink and structured event logging support.
4. Add stub playback backend and controller loop.
5. Update `main.py` so `python -m jukebox` runs the controller until EOF.
6. Add fixture-driven tests for parser, dedupe, and controller behavior.
7. Add optional Spotify backend and its mocked tests.
8. Update README and developer workflow notes once the runtime behavior changes from "initialize and exit" to "run until stopped."

## EPIC 2 Carry-Forward Design Choices

This design intentionally sets up EPIC 2 reuse in three places:

- The controller consumes generic scan lines, so Raspberry Pi specific input can become a new adapter without changing controller logic.
- Playback is behind a backend interface, so the optional EPIC 1 Spotify backend and the later Pi playback backend can share the same dispatch contract.
- Feedback is event-driven, so EPIC 2 can map the same controller events onto LED behavior without redefining the controller state model.

## Open Risks

- Strict 22-character Spotify ID validation may prove too strict in practice and may need relaxing after real-card testing.
- Real Spotify validation depends on user credentials, an available target device, and Premium playback support.
- Terminal-focused scanner validation assumes the scanner behaves as a normal keyboard-wedge device on the development machine.
- The current README mentions `.env.example`, but the file is not present in the repo; implementation should either add it or remove that reference when runtime settings are finalized.
