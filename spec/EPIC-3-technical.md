# EPIC 3 Technical Design

## Purpose

This document turns [spec/EPIC-3-requirements.md](/Users/markus/Workspace/jukebox/spec/EPIC-3-requirements.md) into an implementation design for the current Python repository.
It is intentionally scoped to EPIC 3: harden the Raspberry Pi 3 jukebox into a stable, low-maintenance appliance candidate with observable degraded states, autonomous post-boot playback readiness, and build-readiness notes that fit the current repo and deployment flow.

This design is grounded in the repository structure and EPIC 2 foundation already present at the start of EPIC 3:

- Python 3.11 package code under `src/jukebox`
- existing controller, parser, duplicate gate, `evdev` scanner adapter, and Spotify Web API playback backend from EPIC 2
- `systemd/jukebox.service` plus `systemd/jukebox.env.example`
- SSH/SCP Pi helper scripts under `scripts/`
- Pi setup, deploy, validation, and setup-log documentation already under `docs/`
- automated tests already covering config, controller flow, `evdev`, Spotify playback, and `main.py`

## Selected Decisions Carried Into This Design

This technical design assumes the checked decisions and notes in [spec/EPIC-3-requirements.md](/Users/markus/Workspace/jukebox/spec/EPIC-3-requirements.md):

- EPIC 3 is outcome-driven and may replace the current receiver path if needed to remove phone-side activation after reboot.
- The system exposes a degraded but observable waiting state until autonomous scan-to-playback is actually available, and reserves `ready` for a fully usable runtime.
- Transient failures use bounded unattended recovery with a stable long-running service baseline instead of restart-looping.
- Network recovery scope is limited to same-LAN Wi-Fi reconnect and temporary Spotify/API availability issues.
- The required state model is defined in software now and may map to hardware indicators later, but EPIC 3 does not implement LED wiring.
- Build-readiness deliverables stay at the level of high-level runtime-sensitive notes, not full enclosure construction guidance.
- The repo must provide minimum operator guidance for routine validation, recovery checks, and safe troubleshooting after assembly.
- EPIC 3 validation includes repeated clean reboot checks plus at least one controlled power-cycle test and one temporary network interruption recovery test.

This design also makes one explicit implementation assumption under `D-1`:

- `spotifyd` becomes the single supported receiver-service baseline for EPIC 3 because the recorded 2026-03-08 EPIC 2 validation in [docs/pi-setup-log.md](/Users/markus/Workspace/jukebox/docs/pi-setup-log.md) showed that the current `raspotify` path did not satisfy autonomous post-boot receiver visibility on this Pi.
- The design treats controller-side Spotify Web API auth and receiver-side Spotify Connect session persistence as separate concerns that must both be correct for the device to become usable after boot.

## Design Goals

- Keep the existing controller, parser, duplicate suppression, and scan semantics intact.
- Keep `jukebox.service` running through transient receiver, scanner, and network problems instead of treating them as fatal startup conditions.
- Emit a clear software state model for booting, degraded dependency states, recovery, and readiness.
- Keep the application receiver-agnostic at the code boundary so the supported receiver package can be changed without rewriting controller logic.
- Preserve the current headless env-file deployment model and lightweight SSH/SCP workflow.
- Add only the minimum Python-side complexity needed for stable degraded-state handling on Raspberry Pi 3.
- Make playback targeting resilient to unstable device IDs and boot-time device-list changes.

## Non-Goals

- No GPIO, LED wiring, button integration, or other hardware-control implementation.
- No queueing, local media fallback, or expanded playback modes.
- No attempt to make the app programmatically prove speaker audibility.
- No hotspot flow, offline mode, OTA update path, or read-only filesystem work.
- No full enclosure design or construction plan beyond the runtime-sensitive notes required by EPIC 3.

## EPIC 3 Starting Baseline

The repository already contains the EPIC 2 runtime and deployment foundation that EPIC 3 should extend directly:

- [src/jukebox/main.py](/Users/markus/Workspace/jukebox/src/jukebox/main.py) emits `booting`, builds runtime dependencies, then emits `ready` immediately after `build_runtime()` succeeds.
- [src/jukebox/runtime.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime.py) treats receiver auth failure or scanner-open failure as fatal startup errors and returns no long-running health object.
- [src/jukebox/adapters/playback_spotify.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_spotify.py) can resolve a target device during dispatch and confirm playback start, but its `probe()` only verifies token refresh.
- the current runtime contract only captures controller-side Spotify Web API credentials; it does not yet define receiver-side OAuth bootstrap, persistent session or cache handling, or the required playback scopes for the Python app.
- [src/jukebox/adapters/input_evdev.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/input_evdev.py) opens the scanner once and does not model reconnect or degraded runtime states.
- [src/jukebox/adapters/feedback.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/feedback.py) renders scanner and receiver errors but does not distinguish network degradation.
- [systemd/jukebox.service](/Users/markus/Workspace/jukebox/systemd/jukebox.service) is still coupled to `raspotify.service` through `After=` and `Wants=`.
- [scripts/pi-bootstrap.sh](/Users/markus/Workspace/jukebox/scripts/pi-bootstrap.sh) and [scripts/pi-smoke.sh](/Users/markus/Workspace/jukebox/scripts/pi-smoke.sh) still hard-code `raspotify.service`.
- [docs/pi-validation.md](/Users/markus/Workspace/jukebox/docs/pi-validation.md) still treats “receiver process up but not yet visible to Spotify” as an acceptable post-boot state for EPIC 2.

The main EPIC 3 gaps are therefore:

- readiness is still a one-shot startup decision rather than a runtime state
- receiver visibility after reboot is still not part of the supported baseline
- the controller-auth versus receiver-session boundary is not yet modeled explicitly
- the playback backend still reads as if one device lookup and one play request are enough
- transient failures still rely too heavily on startup retries and manual interpretation
- the receiver service is still hard-coded into docs and scripts

## Spec Alignment Notes

There are three important tensions between the checked decisions, the new receiver findings, and the current implementation shape.

### Controller API Auth Is Not Receiver Readiness

The current EPIC 2 code path treats successful Web API auth as the main startup proof for the playback backend.
The new findings make that too weak: the controller app's refresh token only proves API access, not receiver-session persistence or Connect visibility.

Resolution:

- keep controller-side Spotify Web API credentials in `/etc/jukebox/jukebox.env`
- document receiver-side `spotifyd` OAuth bootstrap and persistent cache separately in the Pi setup docs
- make runtime readiness depend on current receiver visibility, not only on successful token refresh

### Boot-Time Device Assumptions Are Unsafe

The new findings also clarify that device IDs and device availability should be treated as unstable across reboot and reconnect.
That makes a cached boot-time device assumption unsafe even if the target name stays the same.

Resolution:

- treat `JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME` as the stable target identity
- refetch devices on each readiness probe and each dispatch attempt
- use an ephemeral device ID only for the current transfer or play attempt
- classify “target not listed” separately from “transfer failed” and “controller auth failed”

### D-6 vs FR-7 and AC-7

`D-6` was checked as “high-level enclosure notes,” while [spec/EPIC-3-requirements.md](/Users/markus/Workspace/jukebox/spec/EPIC-3-requirements.md) still asks for build-readiness constraints that are actionable enough to avoid blocking enclosure work.

Resolution:

- EPIC 3 will not create a construction spec or detailed enclosure design document.
- Instead, it will add one short “Build Readiness Notes” section to [docs/pi-validation.md](/Users/markus/Workspace/jukebox/docs/pi-validation.md).
- That section will stay limited to runtime-sensitive notes: scanner access assumptions, cable routing assumptions, power access, and service access.

This satisfies the checked “high-level notes” decision without diluting `FR-7`.

## Architecture

```text
Browser machine
  -> controller refresh token with required Web API scopes
  -> spotifyd OAuth bootstrap

Spotify Connect receiver service on Pi
  -> supported EPIC 3 baseline: spotifyd.service
  -> persistent OAuth/session material
  -> persistent cache directory
  -> USB ALSA output
  -> external powered speaker

systemd
  -> network-online.target
  -> spotifyd.service
  -> jukebox.service

jukebox.service
  -> python -m jukebox
  -> build_runtime()
       -> RecoveringEvdevScannerInput
       -> SpotifyPlaybackBackend
       -> RuntimeHealthMonitor
  -> Controller
       -> parser
       -> duplicate gate
       -> playback dispatch
       -> event sinks
            -> terminal feedback
            -> structured logging

RuntimeHealthMonitor
  -> scanner status probe
  -> controller Web API auth probe
  -> Spotify receiver visibility probe
  -> network/API error classification
  -> ready / controller_auth_unavailable / scanner_unavailable / receiver_unavailable / network_unavailable events

SpotifyPlaybackBackend dispatch
  -> refresh access token
  -> fetch current devices
  -> resolve target by name
  -> transfer playback
  -> start requested URI
  -> confirm playback on current device

docs + scripts
  -> pi-setup.md: receiver bring-up and Pi setup
  -> pi-validation.md: repeated reboot, network, power-cycle, and build-readiness checks
  -> pi-smoke.sh: receiver visibility and repeated reboot validation
```

The core controller stays unchanged in responsibility: it still processes complete scan lines and dispatches playback.
EPIC 3 adds long-running readiness supervision around it rather than moving recovery logic into the controller itself.

## Runtime Flow

### Boot and Service Start

1. The Pi boots and reaches `network-online.target`.
2. `spotifyd.service` is enabled separately and starts as the supported receiver service, using separately provisioned headless OAuth credentials and a persistent cache directory.
3. `jukebox.service` starts independently of the receiver unit and runs `python -m jukebox`.
4. [src/jukebox/main.py](/Users/markus/Workspace/jukebox/src/jukebox/main.py) loads config, configures logging, and emits `booting`.
5. [src/jukebox/runtime.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime.py) constructs:
   - a reconnect-capable `EvdevScannerInput`
   - a `SpotifyPlaybackBackend`
   - a `RuntimeHealthMonitor`
6. The health monitor starts polling dependency status immediately.
7. The health monitor evaluates:
   - scanner availability
   - controller-side Spotify Web API auth
   - current device visibility for the configured target name
   - network or discovery failures that prevent reliable device visibility checks
8. While controller auth is invalid, the receiver is not visible, the network or discovery path is unavailable, or the scanner cannot be opened, the monitor emits the corresponding degraded event instead of `ready`.
9. Once both scanner and playback path are healthy enough for autonomous scan-to-playback, the monitor emits `ready`.
10. The input loop and controller remain running across degraded and recovery transitions; they are no longer tied to a one-shot startup probe.

### Per-Scan Handling

1. The scan loop continues to use [src/jukebox/core/controller.py](/Users/markus/Workspace/jukebox/src/jukebox/core/controller.py) unchanged for parse, duplicate suppression, and dispatch behavior.
2. If the system is already `ready`, scans behave the same as EPIC 2.
3. If the system is degraded and a scan occurs anyway, the controller still processes it and dispatch either succeeds or fails normally; EPIC 3 does not add queuing or deferred replay.
4. On each accepted scan, `SpotifyPlaybackBackend.dispatch()` performs the full control sequence:
   - refresh the controller access token
   - refetch the current `/me/player/devices` snapshot
   - resolve the configured target by current device name instead of trusting a cached device ID
   - transfer playback to the current device ID
   - start the requested URI
   - confirm playback against the current device snapshot
5. If the target is not listed or transfer fails, the backend refetches device state and performs one bounded retry before returning failure.
6. A successful dispatch still records duplicate state only after playback confirmation succeeds.
7. A failed dispatch continues to emit `playback_dispatch_failed`, while the background health monitor separately keeps the runtime readiness state up to date.

This preserves existing scan semantics and keeps degraded-state handling orthogonal to the controller.

### Recovery Flow

1. If the scanner path disappears or becomes unreadable, the input adapter stops reporting ready and retries open in-process after a short delay.
2. If controller-side Spotify Web API auth fails, the health monitor emits `controller_auth_unavailable` and continues polling without exiting the process.
3. If Spotify device visibility disappears or the Spotify API cannot be reached, the health monitor emits `receiver_unavailable` or `network_unavailable` and continues polling.
4. When the dependency recovers, the monitor emits `ready` again.
5. `systemd` remains configured with `Restart=on-failure`, but that becomes a last-resort safety net for unhandled exceptions rather than the primary recovery model.

## Module Plan

The implementation should stay close to the current package layout and deployment scaffolding.

### Existing Files to Extend

- [src/jukebox/main.py](/Users/markus/Workspace/jukebox/src/jukebox/main.py)
  Purpose: stop emitting `ready` immediately after startup, start and stop the health monitor, and keep exit-code behavior limited to true fatal failures.
- [src/jukebox/config.py](/Users/markus/Workspace/jukebox/src/jukebox/config.py)
  Purpose: validate the new health-monitor poll setting and document the controller-side Spotify credential contract cleanly.
- [src/jukebox/runtime.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime.py)
  Purpose: build health-aware adapters and return a long-running monitor object alongside the controller dependencies.
- [src/jukebox/adapters/input_evdev.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/input_evdev.py)
  Purpose: become reconnect-capable and expose scanner health status without requiring process restart.
- [src/jukebox/adapters/playback_spotify.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_spotify.py)
  Purpose: add controller-auth, device-discovery, transfer-playback, retry, and failure-classification logic in addition to dispatch-time confirmation.
- [src/jukebox/adapters/playback_stub.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_stub.py)
  Purpose: satisfy the new health-probe contract for local development and tests.
- [src/jukebox/adapters/feedback.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/feedback.py)
  Purpose: render `controller_auth_unavailable`, `network_unavailable`, and repeated `ready` recovery transitions cleanly.
- [systemd/jukebox.service](/Users/markus/Workspace/jukebox/systemd/jukebox.service)
  Purpose: decouple `jukebox.service` from a receiver-specific unit dependency and keep `Restart=on-failure` as a safety net only.
- [systemd/jukebox.env.example](/Users/markus/Workspace/jukebox/systemd/jukebox.env.example)
  Purpose: document any new app-level health-monitor configuration and annotate the required controller-side playback scopes.
- [scripts/pi-bootstrap.sh](/Users/markus/Workspace/jukebox/scripts/pi-bootstrap.sh)
  Purpose: stop hard-coding `raspotify.service`, default to `spotifyd.service`, and validate that the supported receiver service has its config and persistent cache paths in place before bootstrap completes.
- [scripts/pi-smoke.sh](/Users/markus/Workspace/jukebox/scripts/pi-smoke.sh)
  Purpose: assert receiver visibility as part of EPIC 3 readiness, support repeated reboot checks, and surface controller-auth, device-not-listed, transfer-failed, and network-discovery failure modes separately.
- [docs/pi-setup.md](/Users/markus/Workspace/jukebox/docs/pi-setup.md)
  Purpose: switch the supported receiver bring-up path from `raspotify` to `spotifyd`, document manual headless OAuth bootstrap and persistent cache/session handling, and keep USB-audio guidance and env-file setup.
- [docs/pi-validation.md](/Users/markus/Workspace/jukebox/docs/pi-validation.md)
  Purpose: define the EPIC 3 validation contract, including repeated reboot checks, network interruption handling, controlled power-cycle guidance, and high-level build-readiness notes.
- [README.md](/Users/markus/Workspace/jukebox/README.md)
  Purpose: update the runtime and Pi-workflow summary to reflect the EPIC 3 baseline.

### New Runtime Module

- `src/jukebox/runtime_health.py`
  Purpose: hold the runtime-health dataclass, the monitor loop, dependency-priority logic, and transition suppression so the rest of the runtime stays small.

### New Test Module

- `tests/test_runtime_health.py`
  Purpose: cover degraded-to-ready transitions, priority ordering, and duplicate event suppression without needing Pi hardware.

## Data Model

EPIC 3 should introduce one small runtime-specific status object instead of reusing `PlaybackResult` for readiness.

### `DependencyStatus`

Place this in `src/jukebox/runtime_health.py` rather than `core/models.py` because it is runtime supervision data, not controller-domain data.

Proposed shape:

```python
@dataclass(frozen=True)
class DependencyStatus:
    code: str
    ready: bool
    message: str
    reason_code: str | None = None
    backend: str | None = None
    device_name: str | None = None
    source: str | None = None
```

Supported `code` values in EPIC 3:

- `ready`
- `controller_auth_unavailable`
- `scanner_unavailable`
- `receiver_unavailable`
- `network_unavailable`

Usage:

- `EvdevScannerInput.status()` returns `ready` or `scanner_unavailable`.
- `SpotifyPlaybackBackend.status()` returns `ready`, `controller_auth_unavailable`, `receiver_unavailable`, or `network_unavailable`.
- `RuntimeHealthMonitor` chooses the highest-priority non-ready status and emits the matching `ControllerEvent`.

Priority order:

1. `scanner_unavailable`
2. `controller_auth_unavailable`
3. `network_unavailable`
4. `receiver_unavailable`
5. `ready`

This gives operators one actionable primary cause at a time instead of emitting overlapping degraded events on every poll.

### Playback Failure Reason Codes

EPIC 3 should keep the top-level state model compact, but it should standardize the detailed reason codes surfaced through degraded events and `playback_dispatch_failed`.

Required reason-code coverage:

- `spotify_api_auth_error`
- `device_not_listed`
- `connect_transfer_failed`
- `network_discovery_failed`
- `spotify_start_not_confirmed`

The first four are the minimum failure classes needed to reflect the new receiver findings accurately.

## Configuration Design

EPIC 3 keeps the current `/etc/jukebox/jukebox.env` model and only adds the minimum new app-level tuning surface.

### App Configuration

Keep these current variables unchanged:

- `JUKEBOX_INPUT_BACKEND`
- `JUKEBOX_SCANNER_DEVICE`
- `JUKEBOX_PLAYBACK_BACKEND`
- `JUKEBOX_SPOTIFY_CLIENT_ID`
- `JUKEBOX_SPOTIFY_CLIENT_SECRET`
- `JUKEBOX_SPOTIFY_REFRESH_TOKEN`
- `JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME`
- `JUKEBOX_SPOTIFY_DEVICE_ID`
- `JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS`
- `JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS`

Interpretation:

- `JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME` remains the supported appliance target identity
- `JUKEBOX_SPOTIFY_DEVICE_ID` remains available only as a troubleshooting override and must not be treated as a stable boot-safe baseline for EPIC 3

Controller-side auth contract:

- the refresh token used by the Python app must have `user-read-playback-state`
- the refresh token used by the Python app must have `user-modify-playback-state`
- the technical design assumes those scopes are obtained manually on another machine and copied into `/etc/jukebox/jukebox.env`

Add one new app variable:

- `JUKEBOX_HEALTH_POLL_INTERVAL_SECONDS`
  Default: `5.0`
  Purpose: control how often the runtime monitor polls scanner and Spotify readiness.

Validation rules:

- it must be a positive float
- it should default conservatively to avoid excessive Spotify API polling on Raspberry Pi 3

### Receiver-Service Operational Configuration

The application itself should remain receiver-service agnostic.
Receiver-package selection stays in Pi docs and shell scripts, not in the app env file.

For the supported EPIC 3 `spotifyd` path, the operational docs must define:

- a manual headless OAuth bootstrap flow performed on a browser-capable machine
- copying the resulting receiver credentials onto the Pi
- a persistent receiver cache or session directory that survives reboot
- a clear separation between receiver-service credentials and controller app credentials

For shell scripts and docs, add:

- `JUKEBOX_PI_RECEIVER_SERVICE_NAME`
  Default: `spotifyd.service`
  Purpose: let `pi-bootstrap.sh` and `pi-smoke.sh` check the supported receiver service without hard-coding `raspotify.service` into the scripts forever.

### `systemd` Design

[systemd/jukebox.service](/Users/markus/Workspace/jukebox/systemd/jukebox.service) should change in one important way:

- keep `After=network-online.target`
- keep `Wants=network-online.target`
- remove the direct `After=` and `Wants=` dependency on `raspotify.service`

Reason:

- the app is now responsible for degraded-state waiting and readiness transitions
- direct receiver-unit coupling would keep the old “receiver must be up before app starts” assumption that EPIC 3 is intentionally removing

## Feedback and Logging Design

EPIC 3 keeps the current event-sink pattern and extends the event vocabulary rather than adding a new observability subsystem.

### Event Model

Keep existing scan and playback events:

- `booting`
- `ready`
- `scan_received`
- `scan_accepted`
- `duplicate_suppressed`
- `invalid_payload`
- `unsupported_content`
- `playback_dispatch_succeeded`
- `playback_dispatch_failed`

Retain existing dependency events:

- `controller_auth_unavailable`
- `scanner_unavailable`
- `receiver_unavailable`

Add:

- `network_unavailable`

### Emission Rules

- `booting` is emitted once when the process starts.
- The health monitor emits one dependency-unavailable event when the active degraded cause changes.
- `ready` is emitted when the monitor first reaches all-green status and again whenever the system recovers from a degraded state.
- Scan and playback events continue to be emitted by the controller, not by the health monitor.
- `playback_dispatch_failed` must carry reason codes that distinguish API auth, target-not-listed, transfer failure, and network-discovery failure.

### Terminal Feedback

[src/jukebox/adapters/feedback.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/feedback.py) should keep the current concise one-line style.

Add one new rendering branch:

- `controller_auth_unavailable` -> `[API AUTH] unavailable: <reason_code>`
- `network_unavailable` -> `[NETWORK] unavailable: <reason_code>`

No LED abstraction is added in EPIC 3.
The output remains terminal and journal friendly, but the event vocabulary becomes stable enough to map to future indicators later.

### Structured Logging

[src/jukebox/logging.py](/Users/markus/Workspace/jukebox/src/jukebox/logging.py) can keep the existing JSON field set:

- `event`
- `backend`
- `reason_code`
- `device_name`
- `source`

No new logging schema is required.
The new readiness behavior comes from additional event codes, explicit reason-code coverage, and emitting them only on status transitions.

## Testing Strategy

### Automated Tests

Extend or add these test areas:

- `tests/test_runtime_health.py`
  Cover degraded-to-ready transitions, transition suppression, and priority ordering between scanner, controller-auth, network, and receiver failures.
- `tests/test_playback_spotify.py`
  Add status-probe and dispatch tests for target visible, target missing, Spotify auth failure, transport failure, device refetch on each dispatch, transfer playback, and bounded retry after target-selection failure.
- `tests/test_input_evdev.py`
  Add reconnect tests that simulate missing device, later recovery, and buffer reset after disconnect.
- `tests/test_main.py`
  Verify that `ready` is no longer emitted immediately on startup when the health monitor reports degraded state, and that recovery to `ready` is surfaced.
- `tests/test_config.py`
  Add parsing and validation coverage for `JUKEBOX_HEALTH_POLL_INTERVAL_SECONDS` and the documented controller-auth contract.
- `tests/test_logging.py` or a new `tests/test_feedback.py`
  Cover the new `network_unavailable` rendering and structured logging path.

### Manual Pi Validation

Update [docs/pi-validation.md](/Users/markus/Workspace/jukebox/docs/pi-validation.md) so EPIC 3 validation is explicit:

- repeated clean reboot using the smoke helper
- one controlled power-cycle test recorded manually
- one temporary network interruption test recorded manually
- receiver visibility must be confirmed before the system is considered `ready`
- the reboot validation must be run without opening an official Spotify client
- the diagnostic flow must include same-LAN discovery checks such as mDNS or zeroconf visibility when receiver presence is ambiguous
- audio validation remains manual through the existing USB-sound-card checks
- build-readiness notes must be reviewed before enclosure work begins

## Failure Handling

- Invalid configuration still exits with code `2` from [src/jukebox/main.py](/Users/markus/Workspace/jukebox/src/jukebox/main.py).
- Unhandled application exceptions still exit nonzero and rely on `systemd` restart as a safety net.
- Scanner unavailability is no longer a fatal startup error; it becomes a degraded runtime state with in-process reopen attempts.
- Invalid controller Spotify auth or missing playback scopes become `controller_auth_unavailable`, not a generic receiver failure.
- Receiver invisibility is no longer treated as “close enough to ready”; it becomes a `receiver_unavailable` degraded state until the target appears.
- Device-not-listed and transfer failures are separated from controller-auth and network-discovery failures through explicit reason codes.
- Spotify transport failures map to `network_unavailable` and do not exit the service.
- Audio-path failures remain diagnosable only through validation docs and manual checks because the app cannot observe speaker audibility directly.

## Implementation Sequence

1. Add `runtime_health.py`, `DependencyStatus`, and the monitor loop, plus the new config variable for health-poll interval.
2. Refactor `SpotifyPlaybackBackend` so dispatch becomes `token refresh -> device refetch -> transfer playback -> play -> confirm`, with one bounded retry and explicit failure reason codes.
3. Refactor `EvdevScannerInput` and `StubPlaybackBackend` to expose status probes and support in-process degraded recovery.
4. Update `main.py`, `runtime.py`, and `feedback.py` so `ready` is driven by the health monitor instead of one-shot startup success.
5. Decouple [systemd/jukebox.service](/Users/markus/Workspace/jukebox/systemd/jukebox.service) from `raspotify.service` and make Pi scripts receiver-service configurable with `spotifyd.service` as the supported default.
6. Update [docs/pi-setup.md](/Users/markus/Workspace/jukebox/docs/pi-setup.md), [docs/pi-validation.md](/Users/markus/Workspace/jukebox/docs/pi-validation.md), [README.md](/Users/markus/Workspace/jukebox/README.md), and [docs/pi-setup-log.md](/Users/markus/Workspace/jukebox/docs/pi-setup-log.md) to reflect the new receiver baseline, the separate controller-auth and receiver-session setup flows, and the stricter validation contract.
7. Validate on the Pi with repeated reboot checks, one controlled power-cycle, one temporary network interruption test, no official Spotify client open, and recorded build-readiness notes.

## Open Risks

- The assumption that `spotifyd` solves the post-boot visibility gap still needs on-device validation on this Raspberry Pi 3 and Spotify account.
- Even with `spotifyd`, hobbyist Spotify Connect receivers should still be treated as less appliance-grade than an official Spotify partner stack.
- The health monitor introduces periodic Spotify API traffic; the default poll interval is intentionally conservative, but it still increases background requests.
- Scanner reconnect behavior after USB disconnect may expose edge cases around partial buffered scans that need explicit tests.
- Audio-path validation remains partly manual because the app does not have a trustworthy machine-readable signal for audible speaker output.
