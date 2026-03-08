# EPIC 2 Technical Design

## Purpose

This document turns [spec/EPIC-2-requirements.md](/Users/markus/Workspace/jukebox/spec/EPIC-2-requirements.md) into an implementation design for the current Python repository.
It is intentionally scoped to EPIC 2: move the validated EPIC 1 controller onto Raspberry Pi 3, bind it to a real USB scanner, target an on-device Spotify Connect receiver, and prove the first end-to-end V1 playback milestone.

This design is grounded in the current repo state:

- Python 3.11 package scaffold under `src/jukebox`
- `python -m jukebox` as the canonical entrypoint
- existing controller, parser, duplicate gate, and playback abstraction from EPIC 1
- `systemd/jukebox.service` as an incomplete Pi deployment scaffold
- flat local helper scripts under `scripts/`
- no `docs/` directory yet

## Selected Decisions Carried Into This Design

This technical design assumes the checked decisions and notes in [spec/EPIC-2-requirements.md](/Users/markus/Workspace/jukebox/spec/EPIC-2-requirements.md):

- `raspotify` is the supported Spotify Connect receiver for EPIC 2.
- Pi setup becomes repeatable documentation under `docs/` and replaces the current `spec/pisetup.md` note.
- Same-LAN Wi-Fi plus SSH is the only required network posture in EPIC 2.
- A clean boot must return the Pi to scan-ready state through the documented V1 startup path.
- Scanner binding must be consistent across reboots.
- EPIC 2 does not include LED work.
- The baseline audio path is a USB sound card on the Pi, with the 3.5 mm analog output documented only as a fallback troubleshooting path.
- Playback success requires both software-visible confirmation and audible playback, with the test stack able to confirm playback start without relying on human hearing alone.
- EPIC 1 scan semantics stay in place on the Pi unless a Pi-specific issue forces an explicit exception.
- Deployment and reboot validation should be scriptable over SSH/SCP for the agent workflow, but not fully automated from SD imaging onward.
- Runtime secrets stay out of the repository and out of committed files.

## Design Goals

- Reuse the EPIC 1 controller, parser, duplicate suppression, and logging structure rather than introduce a second application shape.
- Add Raspberry Pi specific behavior at the adapter boundary only.
- Keep the local `stdin` workflow working so non-Pi development remains practical.
- Make the Pi runtime deterministic enough for clean boot and clean reboot validation.
- Use the existing Spotify Web API backend as the control path to the selected `raspotify` receiver instead of adding a second playback control stack.
- Keep deployment lightweight and scriptable with SSH, SCP, `systemd`, and a repo-managed environment file template.

## Non-Goals

- No GPIO, LED, button, or enclosure-control work in EPIC 2.
- No internal speaker or amplifier integration.
- No hotspot flow, Ethernet fallback, or offline playback mode.
- No long-run recovery logic beyond the clean-boot and clean-reboot baseline.
- No queue mode, local media fallback, or richer playback controls.

## Current Baseline

The repository already provides a solid EPIC 1 base that EPIC 2 should extend directly:

- [main.py](/Users/markus/Workspace/jukebox/src/jukebox/main.py) assembles the runtime, selects the playback backend, and runs the controller loop.
- [config.py](/Users/markus/Workspace/jukebox/src/jukebox/config.py) already validates environment-driven settings and fast-fails on missing Spotify credentials.
- [core/controller.py](/Users/markus/Workspace/jukebox/src/jukebox/core/controller.py) owns parse, duplicate, and dispatch flow.
- [adapters/input.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/input.py) already defines a line-oriented input contract through `readline()`.
- [adapters/playback_spotify.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_spotify.py) already refreshes tokens and dispatches playback through the Spotify Web API.
- [logging.py](/Users/markus/Workspace/jukebox/src/jukebox/logging.py) already supports structured JSON logging.
- [systemd/jukebox.service](/Users/markus/Workspace/jukebox/systemd/jukebox.service) already establishes the intended service placement and environment-file pattern.

The main EPIC 2 gaps are:

- the runtime still depends on `stdin`, which is not sufficient for a headless `systemd` service using a USB scanner
- the Spotify backend treats a 2xx play request as success, but EPIC 2 requires actual playback-start confirmation
- the repo does not yet contain Pi deployment scripts or `docs/`-based operational documentation

## Spec Alignment Notes

There are three important tensions between the selected EPIC 2 decisions and the current EPIC 1 implementation.

### 1. `stdin` Is Not a Viable Pi Service Input

EPIC 1 used `stdin` intentionally because it worked for local typing and keyboard-wedge scanners in a focused terminal.
That does not work once the app is started by `systemd` on a headless Pi.

Resolution:

- keep `stdin` as the default local input path
- add a Linux-only event-device scanner adapter selected by configuration
- continue feeding newline-complete strings into the existing controller so scan semantics stay unchanged

### 2. Dispatch Success Is Not Enough for EPIC 2

The current Spotify backend reports success as soon as the play request returns 2xx.
That satisfies EPIC 1 dispatch validation, but not EPIC 2's selected requirement to confirm playback start without relying only on human hearing.

Resolution:

- continue using the Spotify Web API control path
- extend the backend to resolve the `raspotify` target device and poll playback state after dispatch
- treat `ok=True` as "playback confirmed on the expected device", not just "request accepted"

This gives the software stack a machine-readable success signal while leaving the final audible-speaker check as a manual hardware smoke test.

### 3. Pi Setup Guidance Must Move Out of `spec/`

[spec/pisetup.md](/Users/markus/Workspace/jukebox/spec/pisetup.md) is operational documentation, not an authoritative product spec.
The checked EPIC 2 decision requires Pi workflow docs under `docs/`, with the root README acting as an index.

Resolution:

- create `docs/` for Pi bring-up, deployment, and validation notes
- migrate useful content from `spec/pisetup.md` into those docs
- remove or replace `spec/pisetup.md` with a short pointer so the repo does not carry two conflicting Pi setup guides

## Architecture

```text
USB HID scanner
  -> /dev/input/by-id/...-event-kbd
  -> EvdevScannerInput
  -> ScanLineReader
  -> Controller
       -> Spotify URI parser
       -> Duplicate gate
       -> SpotifyPlaybackBackend
            -> token refresh
            -> device discovery
            -> play request
            -> playback confirmation poll
       -> event sinks
            -> terminal/status output
            -> structured logs

raspotify.service
  -> Spotify Connect receiver on the Pi
  -> ALSA USB audio output
  -> external powered speaker

systemd
  -> raspotify.service
  -> jukebox.service

scripts/
  -> Pi bootstrap over SSH
  -> Pi deploy via SCP + remote install
  -> Pi smoke/reboot validation

docs/
  -> pi-setup.md
  -> pi-deploy.md
  -> pi-validation.md
```

The core controller remains unchanged in shape: it still accepts complete scan lines and produces controller events.
All Pi-specific behavior lives in adapters, startup checks, scripts, and documentation.

## Runtime Flow

### Boot and Service Start

1. The Pi boots Raspberry Pi OS Lite and joins the configured Wi-Fi network.
2. `network-online.target` becomes active.
3. `raspotify.service` starts and registers a Spotify Connect device with a deterministic configured device name.
4. `jukebox.service` starts `python -m jukebox` with `/etc/jukebox/jukebox.env`.
5. `main.py` loads settings and configures logging.
6. `main.py` builds the configured scan input and playback backend.
7. `main.py` performs startup probes:
   - open the configured scanner device
   - authenticate to Spotify
   - confirm that the configured `raspotify` target device is visible
8. If startup probes fail for a transient reason, the process exits with code `1` and `systemd` retries it.
9. If configuration is invalid, the process exits with code `2` and `systemd` does not loop forever on the bad config.
10. Once probes pass, the process emits a ready/idle event and waits for scans.

This uses `systemd` restart behavior for boot sequencing and transient bring-up races instead of embedding complex recovery logic into the app in EPIC 2.

### Per-Scan Handling on Pi

1. `EvdevScannerInput.readline()` blocks until the scanner emits a full newline-terminated payload.
2. `ScanLineReader` yields the raw line.
3. `Controller.process_line()` performs the same EPIC 1 parse, validation, duplicate, and replace-current-playback flow.
4. On a valid accepted scan, `SpotifyPlaybackBackend.dispatch()`:
   - refreshes an access token
   - resolves the target `raspotify` device
   - sends the play request for the parsed URI
   - polls playback state until the requested URI is confirmed on the target device or the confirmation timeout expires
5. If confirmation succeeds, the controller records duplicate state and emits a playback-success event.
6. If confirmation fails, the controller emits a playback-failure event and does not update duplicate state.

### Clean Reboot Validation

1. A deploy or validation script triggers `sudo reboot` over SSH.
2. The script waits for SSH to return.
3. It verifies `raspotify.service` and `jukebox.service` are active.
4. It runs a one-shot software playback smoke test by SSHing into the Pi, overriding `JUKEBOX_INPUT_BACKEND=stdin`, and piping a known-good Spotify URI into `python -m jukebox`.
5. The physical scanner path and the external speaker remain a manual validation step, but the remote test verifies that the deployed build, runtime config, Spotify auth, target device selection, and playback confirmation path still work after reboot.

This split is deliberate: EPIC 2 needs the workflow to be scriptable for the agent, but the physical card-scan and audible-speaker checks still require hardware in the loop.

## Module Plan

The implementation should stay close to the current package layout.

### Existing Files to Extend

- [pyproject.toml](/Users/markus/Workspace/jukebox/pyproject.toml)
  Purpose: add a Pi-only optional dependency set such as `.[pi]` so scanner support does not burden non-Pi development.
- [README.md](/Users/markus/Workspace/jukebox/README.md)
  Purpose: become the project entry point and index into `spec/` and `docs/`.
- [main.py](/Users/markus/Workspace/jukebox/src/jukebox/main.py)
  Purpose: assemble the configured input backend, perform startup probes, and keep stable exit codes.
- [config.py](/Users/markus/Workspace/jukebox/src/jukebox/config.py)
  Purpose: validate Pi runtime settings for scanner device selection, receiver targeting, and playback confirmation.
- [adapters/input.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/input.py)
  Purpose: preserve the generic line-based input contract and current `stdin` implementation.
- [adapters/playback_spotify.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_spotify.py)
  Purpose: grow from "dispatch only" into "dispatch plus confirmation" for the Pi target device.
- [adapters/feedback.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/feedback.py)
  Purpose: render service lifecycle and receiver/scanner readiness events cleanly.
- [logging.py](/Users/markus/Workspace/jukebox/src/jukebox/logging.py)
  Purpose: include target-device and startup-stage metadata in structured logs when available.
- [systemd/jukebox.service](/Users/markus/Workspace/jukebox/systemd/jukebox.service)
  Purpose: become the real EPIC 2 service unit instead of a future placeholder.

### New Runtime Modules

- `src/jukebox/adapters/input_evdev.py`
  Purpose: Linux event-device scanner adapter that exposes the existing `readline()` contract.
- `src/jukebox/runtime.py`
  Purpose: small app-lifecycle helpers for startup probes and input-backend construction so `main.py` does not become a Pi-specific grab bag.

`runtime.py` is the main EPIC 2 addition on the application side.
It keeps controller logic and adapter logic separate while giving `main.py` a thin orchestration surface.

### New Support Files

- `systemd/jukebox.env.example`
  Purpose: tracked example of the Pi service environment file shape without real secrets.
- `scripts/pi-bootstrap.sh`
  Purpose: initial SSH-based Pi package/bootstrap workflow after the SD image already exists.
- `scripts/pi-deploy.sh`
  Purpose: SCP-based code sync plus remote venv install and service restart.
- `scripts/pi-smoke.sh`
  Purpose: remote service status, software playback smoke test, and optional clean-reboot validation.
- `docs/pi-setup.md`
  Purpose: Raspberry Pi OS Lite imaging, Wi-Fi, SSH, `raspotify`, scanner path discovery, and base runtime setup.
- `docs/pi-deploy.md`
  Purpose: SSH/SCP-based agent-friendly deployment workflow.
- `docs/pi-validation.md`
  Purpose: scanner test, playback confirmation test, USB-audio check, and clean-reboot checklist.

## Input Design

### Configurable Input Backends

EPIC 2 should introduce an explicit input-backend setting:

- `stdin`
  Default for local development and existing tests.
- `evdev`
  Required on the Pi service.

Proposed configuration:

- `JUKEBOX_INPUT_BACKEND=stdin|evdev`
- `JUKEBOX_SCANNER_DEVICE=/dev/input/by-id/...-event-kbd` required when using `evdev`

### `EvdevScannerInput`

`EvdevScannerInput` should implement the same `ReadableInput` protocol already used by [adapters/input.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/input.py):

```python
class ReadableInput(Protocol):
    def readline(self) -> str: ...
```

Behavior:

- open the configured event-device path
- read key events until newline/enter
- convert the limited Spotify-URI character set into a line of text
- return one newline-terminated string per completed scan
- ignore key-release noise and incomplete empty scans

Design choice:

- use `evdev` as the single new Pi runtime dependency, installed through a `pi` optional dependency set
- keep the import local to the `evdev` adapter path so non-Pi development and most tests still work without it

Reason:

- a focused-terminal `stdin` path is not viable under `systemd`
- a small Linux input dependency is lower risk than hand-parsing kernel input events in EPIC 2
- the dependency is tightly scoped to one adapter and does not leak into core logic

### Stable Scanner Binding

The selected scanner binding rule is configuration-driven and path-based, not hardware-ID-hardcoded in the repo:

- docs instruct the operator to identify the stable `/dev/input/by-id/...-event-kbd` path for the installed scanner
- that exact path is stored in `/etc/jukebox/jukebox.env` as `JUKEBOX_SCANNER_DEVICE`
- `jukebox.service` gets read permission through `SupplementaryGroups=input`

This avoids inventing scanner vendor/product identifiers in the spec while still producing stable behavior across reboots.

## Playback and Receiver Design

### Keep Spotify Web API Control, Add Receiver Awareness

EPIC 2 should continue using [adapters/playback_spotify.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_spotify.py) as the only playback-control adapter.

New responsibilities:

- resolve the configured `raspotify` receiver device before a scan is accepted as playable
- dispatch the play request to that target
- confirm that playback actually started on the expected device

This avoids inventing a second playback control path while taking advantage of the backend that already exists in the repo.

### Target Device Resolution

The current backend accepts `JUKEBOX_SPOTIFY_DEVICE_ID`.
EPIC 2 should prefer a deterministic device name and treat raw device ID as an optional override.

Proposed configuration:

- `JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME` required for EPIC 2 Pi deployment
- `JUKEBOX_SPOTIFY_DEVICE_ID` optional override for local troubleshooting only

Backend rules:

- if `JUKEBOX_SPOTIFY_DEVICE_ID` is set, use it directly
- otherwise, call Spotify's devices endpoint and resolve the target by exact device name
- if no matching device is visible, fail with a dedicated `spotify_target_device_unavailable` reason code

This is a better fit for `raspotify`, because the receiver name can be controlled and documented even when the underlying Spotify device ID is not convenient to manage manually.

### Playback Confirmation

After the play request returns success, the backend should poll current playback state for a short bounded window.

Suggested confirmation rules:

- track request:
  confirm `item.uri == request.uri.raw` and target device matches
- album or playlist request:
  confirm `context.uri == request.uri.raw` and target device matches
- all kinds:
  require `is_playing == true`

Suggested defaults:

- `JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS=5.0`
- `JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS=0.25`

If confirmation does not arrive in time, return:

- `ok=False`
- `reason_code="spotify_start_not_confirmed"`

This is the design's answer to the selected note that playback confirmation must not depend on human hearing alone.

### Audio Output Boundary

The Python app does not own audio routing.
EPIC 2 keeps audio concerns outside the application code:

- `raspotify` renders audio
- Raspberry Pi OS and ALSA decide the actual USB audio target
- docs capture the setup and troubleshooting steps for selecting and verifying USB output

The Pi's analog output remains documented only as a fallback troubleshooting path in `docs/pi-validation.md` and `docs/pi-setup.md`.
No app-level audio-path switch is added in EPIC 2.

## Configuration Design

### Existing Variables to Preserve

- `JUKEBOX_ENV`
- `JUKEBOX_LOG_LEVEL`
- `JUKEBOX_LOG_FORMAT`
- `JUKEBOX_PLAYBACK_BACKEND`
- `JUKEBOX_DUPLICATE_WINDOW_SECONDS`
- `JUKEBOX_SPOTIFY_CLIENT_ID`
- `JUKEBOX_SPOTIFY_CLIENT_SECRET`
- `JUKEBOX_SPOTIFY_REFRESH_TOKEN`
- `JUKEBOX_SPOTIFY_DEVICE_ID`

### New Variables for EPIC 2

- `JUKEBOX_INPUT_BACKEND`
  Allowed values: `stdin`, `evdev`
  Default: `stdin`
- `JUKEBOX_SCANNER_DEVICE`
  Required when `JUKEBOX_INPUT_BACKEND=evdev`
- `JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME`
  Required when `JUKEBOX_PLAYBACK_BACKEND=spotify` on the Pi path unless `JUKEBOX_SPOTIFY_DEVICE_ID` is explicitly set
- `JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS`
  Default: `5.0`
  Validation: positive float
- `JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS`
  Default: `0.25`
  Validation: positive float and less than or equal to confirmation timeout

Validation rules:

- `JUKEBOX_INPUT_BACKEND=evdev` requires `JUKEBOX_SCANNER_DEVICE`
- Spotify backend on Pi requires either `JUKEBOX_SPOTIFY_DEVICE_ID` or `JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME`
- confirmation timeout settings must be valid positive floats

### Pi Service Environment File

The tracked example file should live at `systemd/jukebox.env.example`.
The real runtime file remains:

```text
/etc/jukebox/jukebox.env
```

This keeps secrets out of the repo while giving the deployment docs a concrete, repo-managed template to reference.

## Service and Deployment Design

### `systemd` Unit

[systemd/jukebox.service](/Users/markus/Workspace/jukebox/systemd/jukebox.service) should be promoted from scaffold to EPIC 2 baseline.

Key changes:

- `Description=Jukebox controller service`
- `After=network-online.target raspotify.service`
- `Wants=network-online.target raspotify.service`
- `EnvironmentFile=/etc/jukebox/jukebox.env`
- `WorkingDirectory=/opt/jukebox`
- `ExecStart=/opt/jukebox/.venv/bin/python -m jukebox`
- `Restart=on-failure`
- `RestartSec=5`
- `RestartPreventExitStatus=2`
- `SupplementaryGroups=input`
- `StandardInput=null`

This keeps boot behavior simple:

- bad configuration surfaces immediately and does not loop forever
- transient boot ordering issues can be retried by `systemd`
- scanner device access works without running the app as root

### Pi File Layout

EPIC 2 should keep the existing `/opt/jukebox` assumption from the service scaffold:

- `/opt/jukebox` repo checkout or unpacked working tree
- `/opt/jukebox/.venv` runtime virtualenv
- `/etc/jukebox/jukebox.env` secrets and runtime settings

This is the minimum-change design from the current repo scaffold.

### Scripted SSH/SCP Workflow

The deployment workflow should stay flat and scriptable under `scripts/`:

- `scripts/pi-bootstrap.sh`
  Installs required system packages, creates `/opt/jukebox`, and prepares the service environment path.
- `scripts/pi-deploy.sh`
  Creates a tarball from the current working tree excluding local caches and secrets, copies it with `scp`, unpacks it under `/opt/jukebox`, installs the package into `/opt/jukebox/.venv` with the `pi` dependency set, installs or refreshes the service unit, and restarts the service.
- `scripts/pi-smoke.sh`
  Runs remote status checks, journal inspection, a one-shot stdin-driven playback smoke test, and optionally a clean reboot followed by readiness checks.

Suggested script environment variables:

- `JUKEBOX_PI_HOST`
- `JUKEBOX_PI_USER`
- `JUKEBOX_PI_PORT` optional
- `JUKEBOX_PI_ROOT=/opt/jukebox`

These variables are deployment-workflow inputs, not application runtime config.

## Feedback and Logging Design

EPIC 2 keeps the existing event-driven feedback model.
It only widens the state set so service lifecycle and receiver readiness are visible.

### Event Model

The current `ControllerEvent` structure is flexible enough to keep using for EPIC 2, with two small additions:

- `device_name: str | None`
- `source: str | None`

`source` is useful for distinguishing `stdin` from `evdev` when reading logs.

New startup/lifecycle events to emit from `main.py` or `runtime.py`:

- `booting`
- `ready`
- `scanner_unavailable`
- `receiver_unavailable`

Existing per-scan events stay in place:

- `scan_received`
- `scan_accepted`
- `duplicate_suppressed`
- `invalid_payload`
- `unsupported_content`
- `playback_dispatch_succeeded`
- `playback_dispatch_failed`

Design note:

- `playback_dispatch_succeeded` should now mean "playback confirmed on the target device", not merely "HTTP dispatch returned success"

This preserves the existing event code surface while upgrading its meaning for EPIC 2.

### Terminal and Journal Output

[adapters/feedback.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/feedback.py) should render service-relevant lines such as:

```text
[BOOT] waiting for scanner and receiver
[READY] waiting for scan input
[SCAN] spotify:track:...
[ACCEPTED] track spotify:track:...
[PLAYBACK spotify] started track on jukebox
[PLAYBACK spotify] failed: spotify_target_device_unavailable
```

Under `systemd`, stdout and stderr go to the journal, so the same sink remains useful on the Pi and locally.

Structured JSON logging should add `device_name` and `source` when available.

## Documentation Plan

Operational docs should move under a new `docs/` directory:

- `docs/pi-setup.md`
  Covers Raspberry Pi OS Lite imaging, Wi-Fi, SSH, required packages, `raspotify` installation, USB-audio configuration, scanner path discovery, and service env file setup.
- `docs/pi-deploy.md`
  Covers SSH/SCP deployment scripts, expected remote layout, and service update flow.
- `docs/pi-validation.md`
  Covers physical scanner validation, one-shot remote playback smoke tests, USB-speaker check, and clean-reboot checklist.

README changes:

- keep the root README as the overall project entry point
- add links to the authoritative specs in `spec/`
- add links to the Pi setup/deploy/validation docs in `docs/`
- keep local development commands in README, but stop treating it as Pi setup documentation

`spec/pisetup.md` should no longer be the active operational guide once these docs exist.

## Testing Strategy

EPIC 2 testing should stay layered.

### Local Automated Tests

Keep `make check` as the baseline local command and extend coverage with:

- `tests/test_input_evdev.py`
  Covers key-event to line assembly, newline detection, ignored empty scans, and path-validation behavior through test doubles.
- `tests/test_playback_spotify.py`
  Extend coverage for target-device discovery, play-request confirmation polling, confirmation timeout, and receiver-unavailable mapping.
- `tests/test_config.py`
  Add validation for input backend, scanner device path, target device name, and confirmation settings.
- `tests/test_main.py`
  Cover backend selection, startup probe failure exit codes, and service-ready startup behavior.

The test suite should not require real scanner hardware or a live Spotify session.
All external behavior remains mocked at the adapter edge.

### Remote Pi Smoke Tests

`scripts/pi-smoke.sh` should provide a minimal remote validation path:

- verify `systemctl is-active raspotify`
- verify `systemctl is-active jukebox`
- inspect recent `journalctl -u jukebox`
- run a one-shot playback smoke test with:
  - `JUKEBOX_INPUT_BACKEND=stdin`
  - `JUKEBOX_PLAYBACK_BACKEND=spotify`
  - a known-good Spotify URI piped to `python -m jukebox`

This gives the agent a repeatable, non-physical smoke test for deployment correctness and playback-start confirmation.

### Manual Hardware Validation

Manual checks remain necessary for:

- real physical QR card scan through the mounted scanner
- audible USB audio output through the external powered speaker
- confirming that the physical setup matches the documented scanner path and speaker connection

EPIC 2 should document these as manual smoke steps, not pretend they can be fully automated from the repo alone.

## Failure Handling

### Startup Failures

Return code policy:

- `0` clean EOF or intentional stop
- `1` transient startup/runtime failure suitable for `systemd` restart
- `2` invalid configuration
- `130` operator interrupt

Transient startup failures include:

- scanner device missing or unreadable
- `raspotify` target device not yet visible
- Spotify auth transport failure during startup probe

Configuration failures include:

- missing `JUKEBOX_SCANNER_DEVICE` for `evdev`
- missing Spotify credentials
- missing receiver targeting config
- invalid timeout settings

### Per-Scan Failures

Recoverable per-scan failures remain in-band events:

- malformed payload
- unsupported URI type
- duplicate suppression
- target device unavailable
- playback confirmation timeout
- Spotify transport or auth errors during a scan

The controller should continue processing future scans after these failures.

## Implementation Sequence

1. Extend `config.py` for input backend, scanner device, target device name, and confirmation settings.
2. Add `runtime.py` and update `main.py` to build the configured input backend and run startup probes.
3. Add `input_evdev.py` with tests that use fakes rather than real device files.
4. Extend `playback_spotify.py` for target-device discovery and playback confirmation polling.
5. Update terminal feedback and structured logging for startup/ready states and device metadata.
6. Promote `systemd/jukebox.service` into the EPIC 2 baseline unit and add `systemd/jukebox.env.example`.
7. Add `scripts/pi-bootstrap.sh`, `scripts/pi-deploy.sh`, and `scripts/pi-smoke.sh`.
8. Create `docs/pi-setup.md`, `docs/pi-deploy.md`, and `docs/pi-validation.md`, migrating the useful content from `spec/pisetup.md`.
9. Update `README.md` so it indexes specs, docs, and local developer commands cleanly.

## Open Risks

- `raspotify` registration timing may be slower than expected on some boots, increasing dependence on `systemd` retry timing.
- Scanner key mapping can vary across devices and keyboard-layout assumptions; the adapter and docs should stay explicit about the expected keyboard-wedge behavior.
- Spotify Connect control and playback confirmation still depend on Premium account behavior and the same account seeing the Pi receiver.
- Analog Pi output quality may still force the documented USB audio exception path on some hardware.
- The Pi-only `evdev` dependency must be isolated carefully so non-Pi development machines do not become harder to use.
