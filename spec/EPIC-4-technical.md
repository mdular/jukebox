# EPIC 4 Technical Design

## Purpose

This document turns [spec/EPIC-4-requirements.md](/Users/markus/Workspace/jukebox/spec/EPIC-4-requirements.md) into an implementation design for the current Python repository.
It is intentionally scoped to EPIC 4: finish the standalone V1 appliance with clearer feedback, selected card-driven controls, companion setup and auth flows, automatic Wi-Fi fallback, and idle-power behavior while preserving the hardened EPIC 3 runtime.

This design is grounded in the repository structure already present at the start of EPIC 4:

- Python 3.11 package code under `src/jukebox`
- an existing controller, strict Spotify URI parser, duplicate gate, `evdev` scanner adapter, Spotify Web API playback backend, and runtime health monitor
- `systemd/jukebox.service` plus `systemd/jukebox.env.example`
- Pi helper scripts under `scripts/`
- Pi setup, deploy, validation, build, and setup-log docs under `docs/`
- automated tests already covering config, controller flow, feedback rendering, `evdev`, Spotify playback, runtime health, and `main.py`

## Selected Decisions Carried Into This Design

This technical design assumes the checked decisions and notes in [spec/EPIC-4-requirements.md](/Users/markus/Workspace/jukebox/spec/EPIC-4-requirements.md):

- EPIC 4 promotes the existing runtime state model into a clearer user-facing feedback contract.
- Immediate acknowledgement remains distinct from playback confirmation, and the existing Netum NT-91 scanner beep is treated as part of that immediate acknowledgement rather than ignored.
- Stop behavior is card-driven first, not hardware-button driven.
- EPIC 4 reopens broader card-control design and includes the checked D-10 control items in V1 scope.
- Volume remains physically external, and the external-speaker audio baseline remains unchanged even though optional software-side volume preset cards are now in scope.
- The operator flow expands into a browser-based companion configuration interface that can cover setup, receiver auth or re-auth, and selected recovery actions.
- Maintenance ergonomics stay focused and lightweight, including a diagnostic JSON surface rather than a full dashboard.
- EPIC 4 regression validation reuses the EPIC 3 boot, recovery, and scan-to-playback baseline and must rerun the network-interruption checks because the selected scope now touches networking.
- The checked D-10 items are committed EPIC 4 scope, while the unchecked items remain post-roadmap backlog.

This design makes four explicit implementation assumptions so the expanded scope stays concrete:

- The additional setup card selected under D-10 will be implemented as a receiver re-auth entry card, because receiver auth and re-auth are already selected EPIC 4 maintenance flows.
- Replace-versus-queue mode is implemented as `replace` versus `queue_tracks`. Track cards can be queued; album and playlist cards keep replace semantics and surface that limitation honestly.
- Volume preset cards are implemented through Spotify Connect software volume percentages. They complement but do not replace the external speaker's own volume controls.
- Automatic Wi-Fi fallback is a setup-access behavior for missing Wi-Fi configuration, explicit Wi-Fi reset, or sustained boot-time inability to reach a configured network. Ordinary transient runtime outages remain degraded-state recovery, not immediate AP fallback.

## Design Goals

- Keep the current Spotify scan-to-playback behavior intact for ordinary music cards.
- Add explicit non-Spotify control-card support without mixing operator actions into the normal music-card path implicitly.
- Reuse the current event-driven runtime so terminal output, structured logs, the new operator interface, and the idle monitor share one canonical status model.
- Preserve the V1 external-speaker baseline while adding queue toggles, volume presets, and next-track in a way that stays honest about Spotify API limits.
- Isolate privileged Wi-Fi, shutdown, and receiver-auth work behind narrow helper boundaries rather than expanding the main Python process privileges.
- Keep the operator interface lightweight enough for Raspberry Pi 3 by using the Python standard library instead of a heavy web framework.
- Add automatic Wi-Fi fallback and idle auto-shutdown in a way that improves standalone serviceability instead of creating more recovery ambiguity.
- Leave a clear post-standalone review checkpoint for further UX experimentation without under-delivering the selected EPIC 4 scope.

## Non-Goals

- No built-in volume control, internal audio, amplifier integration, or speaker-acoustics work.
- No physical stop button, rotary encoder, next-track button, or GPIO control surface in EPIC 4.
- No broader management dashboard or child-facing daily-use web UI.
- No printer-friendly QR generator, local playback fallback, story cards, podcast cards, or queue mode as the new primary playback model.
- No read-only filesystem mode, OTA updates, or blank-device self-provisioning image pipeline.
- No reimplementation of `spotifyd` credential formats inside the Python app.

## Current Baseline

The repository already contains the hardened EPIC 3 runtime that EPIC 4 should extend directly:

- [src/jukebox/core/parser.py](/Users/markus/Workspace/jukebox/src/jukebox/core/parser.py) only accepts strict Spotify URIs and has no notion of control or setup cards.
- [src/jukebox/core/controller.py](/Users/markus/Workspace/jukebox/src/jukebox/core/controller.py) only routes successful scans into playback dispatch; it cannot execute control, setup, or system actions.
- [src/jukebox/core/models.py](/Users/markus/Workspace/jukebox/src/jukebox/core/models.py) does not yet model control-card intents, control-action results, playback-mode state, or reusable feedback snapshots.
- [src/jukebox/adapters/feedback.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/feedback.py) only renders terminal lines from controller events and does not maintain a reusable feedback snapshot for another surface such as an operator UI.
- [src/jukebox/runtime.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime.py) assembles only input, playback, and the runtime health monitor.
- [src/jukebox/runtime_health.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime_health.py) only merges scanner and playback dependency states and has no explicit setup-required or auth-required mode.
- [src/jukebox/adapters/playback_spotify.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_spotify.py) can transfer and start playback, but it cannot stop playback, skip, queue tracks, set volume presets, or report player activity for idle shutdown decisions.
- [systemd/jukebox.service](/Users/markus/Workspace/jukebox/systemd/jukebox.service) runs as `pi` with no privileged helper path for Wi-Fi changes or clean shutdown.
- [docs/pi-setup.md](/Users/markus/Workspace/jukebox/docs/pi-setup.md) still documents manual Wi-Fi setup through Raspberry Pi Imager and manual off-device `spotifyd authenticate` plus credential-file copy.
- [scripts/pi-smoke.sh](/Users/markus/Workspace/jukebox/scripts/pi-smoke.sh) duplicates a Spotify visibility probe inline instead of reading service-owned health JSON.

The main EPIC 4 gaps are therefore:

- the payload model still assumes every meaningful card is a Spotify URI
- the controller cannot distinguish child-facing music cards from control, setup, and system cards
- the runtime has no persistent operator-state store for playback mode, setup mode, or browser-surface data
- the service has no built-in status JSON or browser-based setup and auth surface
- Wi-Fi recovery, automatic fallback, graceful shutdown, receiver auth, and idle shutdown still depend on manual shell workflows or do not exist
- there is no explicit technical bridge between the selected EPIC 4 experiments and the post-standalone review checkpoint

## Spec Alignment Notes

There are five important tensions between the checked EPIC 4 decisions, the current repo, and the existing EPIC 3 assumptions.

### Control Cards Need an Explicit Namespace

The requirements now include stop, next-track, queue toggles, volume presets, shutdown, Wi-Fi reset, and an additional setup card, but the current repo only has a strict Spotify parser.
That leaves the raw payload format for non-Spotify cards unspecified.

Resolution:

- introduce a private `jukebox:<group>:<action>` payload namespace for non-Spotify cards
- keep Spotify URIs as-is for music cards
- implement these EPIC 4 actions:
  - `jukebox:playback:stop`
  - `jukebox:playback:next`
  - `jukebox:mode:replace`
  - `jukebox:mode:queue`
  - `jukebox:volume:low`
  - `jukebox:volume:medium`
  - `jukebox:volume:high`
  - `jukebox:setup:wifi-reset`
  - `jukebox:setup:receiver-reauth`
  - `jukebox:system:shutdown`

This keeps media parsing strict while giving EPIC 4 a concrete, testable control surface.

### External Volume Baseline vs Volume Preset Cards

The checked requirements keep physical volume external, but the checked D-10 scope now includes volume preset cards.
Those are compatible only if the design treats them as software-side convenience controls rather than a product-direction change.

Resolution:

- keep the external speaker as the only required physical volume surface
- implement volume preset cards through the Spotify Web API volume endpoint
- make the preset percentages explicit config, not hard-coded behavior
- surface `volume_control_unavailable` honestly if the active receiver cannot honor software volume changes

### Queue Toggle vs Supported URI Types

The repo supports `track`, `album`, and `playlist`, but Spotify's queue API is honest only for track-like items.
Pretending full queue support for album and playlist cards would create misleading behavior.

Resolution:

- persist a playback mode of either `replace` or `queue_tracks`
- in `queue_tracks` mode, track cards call the queue path
- album and playlist cards still use the ordinary replace dispatch path
- feedback and docs must make that limitation explicit

This preserves honesty without discarding the selected queue-toggle scope.

### Automatic Wi-Fi Fallback vs Ordinary Network Recovery

The checked scope includes automatic Wi-Fi fallback, but EPIC 3 already established degraded network recovery for normal outages.
If the design switched into AP mode too aggressively, it would weaken the hardened baseline.

Resolution:

- keep ordinary transient network loss as degraded-state recovery
- enter setup fallback automatically only when there is no usable Wi-Fi configuration, Wi-Fi reset was explicitly requested, or boot-time connectivity does not recover within a long setup fallback grace period
- keep the exact OS-network implementation inside a helper boundary so the Python app owns policy, not `/etc` file writing

### In-Scope Experiments vs Post-Standalone Review

The checked D-10 items are now V1 scope, but the user still wants them reviewed again after real standalone use before V2 commits physical controls or richer feedback.

Resolution:

- implement the selected EPIC 4 control and setup cards now
- persist their state clearly enough to observe household usage during validation
- keep the output docs and status JSON explicit about the current selected baseline
- leave a post-standalone review checkpoint focused on whether any card-driven behaviors should graduate into later physical controls or richer standalone UX

## Architecture

```text
Scanned payload
  -> Controller
       -> parse_scan_payload()
            -> SpotifyMediaCard
            -> JukeboxActionCard
       -> if media:
            -> duplicate gate
            -> PlaybackModeResolver
                 -> replace -> PlaybackBackend.dispatch()
                 -> queue_tracks + track -> PlaybackBackend.enqueue()
                 -> queue_tracks + album/playlist -> fallback replace dispatch
       -> if action:
            -> ActionDebounceGate
            -> ActionRouter.execute()
                 -> PlaybackControlAdapter.stop()
                 -> PlaybackControlAdapter.skip_next()
                 -> PlaybackControlAdapter.set_volume_preset()
                 -> OperatorStateStore.set_playback_mode()
                 -> SetupModeManager.request_wifi_reset()
                 -> SetupModeManager.request_receiver_reauth()
                 -> SystemHelperAdapter.request_shutdown()
       -> ControllerEvent stream

ControllerEvent stream
  -> FeedbackStateTracker
  -> TerminalStatusSink
  -> StructuredEventLogger
  -> IdleMonitor

Runtime services
  -> RuntimeHealthMonitor
       -> scanner status
       -> playback status
       -> setup/auth mode status
  -> OperatorHttpServer
       -> HTML setup/auth pages
       -> JSON status endpoint
       -> Wi-Fi setup form
       -> receiver-auth session controls
  -> OperatorStateStore
       -> persisted non-secret state under /var/lib/jukebox
  -> SetupModeManager
       -> invokes privileged Wi-Fi helper scripts
  -> ReceiverAuthCoordinator
       -> invokes spotifyd auth helper
  -> IdleMonitor
       -> tracks last activity and player state
       -> requests graceful shutdown on long idle

systemd
  -> network-online.target
  -> jukebox.service (User=pi)
  -> helper scripts reachable through locked-down sudo rules

docs + scripts
  -> pi-setup.md: developer bootstrap plus appliance setup mode and auth flow
  -> pi-validation.md: control cards, Wi-Fi fallback, idle shutdown, and regression checks
  -> pi-smoke.sh: query service-owned JSON status instead of duplicating probe logic
```

The controller remains the orchestration center for scan outcomes.
EPIC 4 adds a typed action-card path, a shared feedback-state layer, an operator maintenance plane, and an idle monitor around the existing runtime rather than replacing the core playback loop.

## Runtime Flow

### Normal Boot

1. `systemd` starts `jukebox.service` as `pi`.
2. [src/jukebox/main.py](/Users/markus/Workspace/jukebox/src/jukebox/main.py) loads config, configures logging, emits `booting`, and starts the runtime services.
3. [src/jukebox/runtime.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime.py) constructs:
   - the input adapter
   - the playback backend
   - a new action router
   - a new persistent operator-state store
   - a new feedback-state tracker
   - a new operator HTTP server
   - a new setup-mode manager
   - a new idle monitor
   - the runtime health monitor
4. The operator HTTP server starts before scan processing begins so the setup or status surface is available even while the runtime is recovering.
5. The setup-mode manager checks persisted operator state and current Wi-Fi health:
   - if Wi-Fi reset or re-auth was explicitly requested, it enters the corresponding maintenance mode
   - if no usable Wi-Fi config exists or boot-time connectivity does not recover within `JUKEBOX_SETUP_FALLBACK_GRACE_SECONDS`, it requests setup fallback mode
   - otherwise it stays in ordinary client mode
6. The health monitor polls scanner, playback, and setup or auth state.
7. If the device is configured for ordinary client mode and playback becomes available, the runtime emits `ready`.
8. If Wi-Fi setup or receiver re-auth is required, the runtime emits `setup_required` or `auth_required` instead of `ready`, keeps the operator surface available, and does not claim scan-readiness for ordinary playback.

### Media Card Handling

1. The controller reads one newline-terminated payload from the scanner or the current input backend.
2. `parse_scan_payload()` recognizes either:
   - a Spotify media card under the existing strict Spotify URI rules
   - an action card under the new `jukebox:<group>:<action>` namespace
3. For Spotify media cards, duplicate suppression behaves the same as EPIC 3.
4. The controller resolves the current playback mode from operator state:
   - `replace` dispatches exactly like EPIC 3
   - `queue_tracks` enqueues `track` cards
   - `queue_tracks` falls back to replace dispatch for `album` and `playlist` cards and emits an explicit informational event
5. The scanner's built-in beep remains the earliest acknowledgement, but the software still emits `scan_received`, `scan_accepted`, and playback success or failure events so the later feedback surfaces stay in sync.
6. Successful playback or enqueue operations record duplicate state only after the backend confirms success.

### Action Card Handling

1. The parser returns a typed action-card intent rather than rejecting the payload as malformed.
2. The controller routes that intent to an action debounce gate so one physical scan does not accidentally double-trigger stop, shutdown, or setup actions.
3. The action router executes one of these EPIC 4 actions:
   - `playback.stop`
   - `playback.next`
   - `mode.replace`
   - `mode.queue`
   - `volume.low`
   - `volume.medium`
   - `volume.high`
   - `setup.wifi-reset`
   - `setup.receiver-reauth`
   - `system.shutdown`
4. Child-facing actions are playback or mode actions. Operator-facing actions are setup and shutdown actions.
5. Unknown or not-yet-implemented `jukebox:` actions produce a distinct unsupported-action outcome rather than silently doing nothing.

### Action Semantics

- `playback.stop`
  Stops current playback. On Spotify this is implemented as a pause request on the resolved target device, because the Web API exposes pause semantics rather than a true stop primitive.
- `playback.next`
  Calls the Spotify next-track endpoint on the active target device. If there is no active playback context, the action fails with a specific reason instead of pretending success.
- `mode.replace`
  Persists the default EPIC 3 replace behavior in operator state. Subsequent music-card scans use ordinary replacement semantics.
- `mode.queue`
  Persists `queue_tracks` in operator state. Subsequent track-card scans queue; album and playlist scans still replace and emit an explicit fallback message.
- `volume.low`, `volume.medium`, `volume.high`
  Map to configured Spotify volume percentages. Failure is explicit if the target device is missing or software volume is unsupported.
- `setup.wifi-reset`
  Persists a setup-mode request, clears saved client Wi-Fi through the helper, and transitions the device into setup fallback mode.
- `setup.receiver-reauth`
  Persists an auth-required request, marks the operator surface to present the receiver-auth flow prominently, and allows the companion UI to run the wrapped `spotifyd authenticate` sequence without shell access.
- `system.shutdown`
  Emits a shutdown-requested event, stops playback if needed, and invokes a privileged shutdown helper for a graceful OS shutdown.

### Setup and Companion Interface Flow

1. When the device enters setup or auth-required mode, the operator HTTP surface becomes the primary maintenance entrypoint.
2. The status page exposes:
   - the current runtime feedback state
   - playback mode
   - whether setup fallback or auth-required mode is active
   - the currently enabled action-card set
   - the idle-shutdown timer status
3. The Wi-Fi setup page collects the minimum client credentials needed to join the normal home network path.
4. The Python service sends those credentials to a privileged Wi-Fi helper rather than writing system files directly itself.
5. Once Wi-Fi is configured and client mode is restored, the same companion interface offers receiver-auth or re-auth actions.
6. Receiver auth uses a helper that wraps `spotifyd authenticate` on the Pi against the real configured cache path, surfaces the approval URL in the browser UI, and reports session status back to the operator page.
7. After auth succeeds, the helper restarts `spotifyd.service`, and the runtime health monitor waits for the receiver to become visible before returning to `ready`.

### Automatic Wi-Fi Fallback Flow

1. On boot, the setup-mode manager checks whether Wi-Fi setup is already requested or whether a usable client Wi-Fi configuration exists.
2. If Wi-Fi is explicitly reset or no usable client configuration exists, the helper starts the setup AP immediately.
3. If a normal client configuration exists but network reachability does not recover within the configured fallback grace period during boot, the helper can switch the device into setup AP mode automatically.
4. Once the setup AP is active, the operator server remains reachable there and the runtime emits `setup_required` instead of `network_unavailable`.
5. Ordinary runtime outages after the device had already reached `ready` stay in degraded recovery unless the operator later requests a Wi-Fi reset.

### Idle Monitor Flow

1. A new idle monitor consumes controller events and polls the playback backend for current player activity.
2. It records the last meaningful household activity timestamp from:
   - successful media dispatch or enqueue
   - accepted action cards other than shutdown
   - explicit playback or mode changes
3. When `JUKEBOX_IDLE_SHUTDOWN_SECONDS` elapses with no active playback and no recent activity, the idle monitor emits `auto_shutdown_requested`.
4. The shutdown coordinator then requests the same graceful helper path used by the shutdown card.
5. If playback is active, player state is unknown, or setup or auth mode is active, the idle timer does not trigger shutdown.

### Shared Feedback Flow

1. A new feedback-state tracker consumes the same controller and health events already emitted by the runtime.
2. That tracker maintains one current user-facing state snapshot for:
   - terminal output
   - structured logs
   - the operator HTML page
   - the JSON status endpoint
3. The tracker does not attempt to control the scanner beep itself; it only models the software-visible states that follow the beep.
4. If a future LED adapter is added, it will subscribe to the same feedback snapshot instead of building a second state machine.

## Module Plan

The implementation should stay close to the current package layout and add only the minimum new surfaces needed for EPIC 4.

### Existing Files to Extend

- [src/jukebox/main.py](/Users/markus/Workspace/jukebox/src/jukebox/main.py)
  Purpose: start and stop the operator HTTP server, feedback-state tracker, and idle monitor alongside the health monitor.
- [src/jukebox/runtime.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime.py)
  Purpose: assemble the action router, operator-state store, setup-mode manager, idle monitor, and operator server in addition to the current scanner and playback dependencies.
- [src/jukebox/runtime_health.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime_health.py)
  Purpose: add `setup_required` and `auth_required` as blocking not-ready states and allow a third status source for setup/auth health.
- [src/jukebox/config.py](/Users/markus/Workspace/jukebox/src/jukebox/config.py)
  Purpose: validate operator HTTP settings, helper command paths, volume presets, idle-shutdown settings, and setup fallback settings.
- [src/jukebox/core/controller.py](/Users/markus/Workspace/jukebox/src/jukebox/core/controller.py)
  Purpose: route parsed payloads into media playback or action-card execution and honor persisted playback mode.
- [src/jukebox/core/parser.py](/Users/markus/Workspace/jukebox/src/jukebox/core/parser.py)
  Purpose: parse both Spotify media cards and `jukebox:` action cards.
- [src/jukebox/core/models.py](/Users/markus/Workspace/jukebox/src/jukebox/core/models.py)
  Purpose: add typed action-card, action-result, playback-mode, player-state, and feedback-state models.
- [src/jukebox/adapters/feedback.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/feedback.py)
  Purpose: render new action, setup, auth, and shutdown events and expose a shared feedback snapshot.
- [src/jukebox/adapters/playback_spotify.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_spotify.py)
  Purpose: add queue, pause-based stop, next-track, volume preset, and player-state support while keeping that behavior separate from ordinary playback dispatch.
- [src/jukebox/adapters/playback_stub.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_stub.py)
  Purpose: satisfy the new playback-control contract in local development and tests.
- [systemd/jukebox.env.example](/Users/markus/Workspace/jukebox/systemd/jukebox.env.example)
  Purpose: document the operator HTTP port, operator-state path, setup AP settings, volume presets, idle-shutdown timer, and helper command paths.
- [systemd/jukebox.service](/Users/markus/Workspace/jukebox/systemd/jukebox.service)
  Purpose: keep the service as `pi` while documenting the helper boundaries used for Wi-Fi setup, auth, and shutdown.
- [scripts/pi-bootstrap.sh](/Users/markus/Workspace/jukebox/scripts/pi-bootstrap.sh)
  Purpose: install any extra Pi-side packages required for setup fallback and seed the operator-state path and helper installation points.
- [scripts/pi-smoke.sh](/Users/markus/Workspace/jukebox/scripts/pi-smoke.sh)
  Purpose: query the new status JSON surface instead of duplicating Spotify visibility logic inline and add a control-card replay path.
- [docs/pi-setup.md](/Users/markus/Workspace/jukebox/docs/pi-setup.md)
  Purpose: document setup AP behavior, Wi-Fi fallback, receiver auth or re-auth through the companion flow, and operator-only cards.
- [docs/pi-validation.md](/Users/markus/Workspace/jukebox/docs/pi-validation.md)
  Purpose: add manual checks for the selected control cards, setup AP fallback, idle shutdown, operator status JSON, and the setup/auth flow.
- [README.md](/Users/markus/Workspace/jukebox/README.md)
  Purpose: update the repo overview for the operator surface and selected EPIC 4 control baseline.

### New Python Modules

- `src/jukebox/core/cards.py`
  Purpose: hold the typed media-card and action-card intent models plus the `jukebox:` namespace helpers.
- `src/jukebox/adapters/action_router.py`
  Purpose: map parsed action-card intents to concrete runtime actions such as stop, queue mode, Wi-Fi reset, receiver re-auth, and shutdown.
- `src/jukebox/operator_state.py`
  Purpose: load and persist non-secret operator state such as playback mode, setup flags, and last known Wi-Fi mode.
- `src/jukebox/operator_server.py`
  Purpose: serve the minimal HTML setup/auth pages and the JSON status endpoint using the standard library HTTP server.
- `src/jukebox/receiver_auth.py`
  Purpose: coordinate browser-visible receiver-auth sessions around the wrapped `spotifyd authenticate` helper.
- `src/jukebox/adapters/system_helpers.py`
  Purpose: invoke the privileged Wi-Fi, receiver-auth, and shutdown helper commands through a narrow adapter boundary.
- `src/jukebox/feedback_state.py`
  Purpose: maintain the current user-facing feedback snapshot that both the terminal sink and operator server can read.
- `src/jukebox/idle_monitor.py`
  Purpose: track household activity, query player state, and request graceful shutdown after long idle.

### New Non-Python Files

- `scripts/runtime/jukebox-wifi-helper.sh`
  Purpose: apply Wi-Fi client credentials, clear saved Wi-Fi config, and switch between client mode and setup AP mode on the Pi.
- `scripts/runtime/jukebox-spotifyd-auth-helper.sh`
  Purpose: wrap `spotifyd authenticate`, surface the approval URL, and restart `spotifyd.service` after credentials land in the configured cache path.
- `scripts/runtime/jukebox-shutdown-helper.sh`
  Purpose: request an orderly system shutdown for both the shutdown card and the idle monitor path.
- `sudoers/jukebox-maintenance`
  Purpose: allow the `pi` user to run only the runtime helper scripts and the minimum related service commands without granting broad root access.

## Data Model

### Parsed Card Intents

EPIC 4 replaces the one-type parser result with an explicit two-branch model:

- `SpotifyMediaCard`
  Fields: `raw`, `kind`, `spotify_id`
- `JukeboxActionCard`
  Fields: `raw`, `group`, `action`, `action_id`

The parser rules are:

- `spotify:(track|album|playlist):<id>` remains the strict media-card format
- `jukebox:<group>:<action>` becomes the action-card format
- unsupported `jukebox:` actions parse successfully as action cards and are rejected later by the action registry with a specific unsupported-action failure

### Playback Mode State

Persisted operator state carries:

- `replace`
- `queue_tracks`

Default is `replace`.
This lives outside the media-card payload model so ordinary music cards remain unchanged.

### Action Definitions

The action router uses an explicit registry.
Each definition includes:

- action id
- payload triplet
- whether it is child-facing or operator-only
- whether it affects playback, setup mode, system power, or persisted operator state
- whether it should be debounced

The registry shape is intentionally extensible so the post-roadmap experiments can be reviewed later without changing the parser contract.

### Operator State

Persisted non-secret state lives in one JSON file under `/var/lib/jukebox`.
It contains:

- schema version
- current playback mode
- whether setup mode was explicitly requested
- whether receiver re-auth was explicitly requested
- last known Wi-Fi mode from the app's point of view
- which action-card actions are enabled
- idle-shutdown enabled flag if later needed

Secrets do not live there.
Wi-Fi passphrases stay in the OS network configuration managed by the helper, and receiver credentials stay in the `spotifyd` cache path.

### Feedback Snapshot

The feedback-state tracker keeps one in-memory snapshot with:

- current display state such as `booting`, `setup_required`, `auth_required`, `ready`, `scan_acknowledged`, `playback_started`, `playback_failed`, `action_succeeded`, `action_failed`, `shutdown_requested`, or `auto_shutdown_requested`
- last transition timestamp
- current reason code if degraded
- current device name when available
- current playback mode
- last card action metadata for the operator page

The operator JSON endpoint serializes a redacted version of this snapshot.

## Configuration Design

The existing env-file model remains the runtime baseline.
EPIC 4 adds a small number of app-level settings:

- `JUKEBOX_OPERATOR_HTTP_BIND`
  Default: `127.0.0.1` for local development; set to `0.0.0.0` in the Pi env file.
- `JUKEBOX_OPERATOR_HTTP_PORT`
  Default: `8080`
- `JUKEBOX_OPERATOR_STATE_PATH`
  Default: `/var/lib/jukebox/state.json`
- `JUKEBOX_CONTROL_DEBOUNCE_SECONDS`
  Default: `1.0`
- `JUKEBOX_PLAYBACK_MODE_DEFAULT`
  Default: `replace`
- `JUKEBOX_VOLUME_PRESET_LOW_PERCENT`
  Default: `35`
- `JUKEBOX_VOLUME_PRESET_MEDIUM_PERCENT`
  Default: `55`
- `JUKEBOX_VOLUME_PRESET_HIGH_PERCENT`
  Default: `75`
- `JUKEBOX_IDLE_SHUTDOWN_SECONDS`
  Default: disabled in local development; explicitly set in the Pi env file
- `JUKEBOX_SETUP_AP_SSID`
  Default: none for local development; required in the Pi env file when setup fallback is enabled
- `JUKEBOX_SETUP_AP_PASSPHRASE`
  Default: none
- `JUKEBOX_SETUP_FALLBACK_GRACE_SECONDS`
  Default: `120`
- `JUKEBOX_WIFI_HELPER_COMMAND`
  Default install target: `/usr/local/libexec/jukebox-wifi-helper`
- `JUKEBOX_SPOTIFYD_AUTH_HELPER_COMMAND`
  Default install target: `/usr/local/libexec/jukebox-spotifyd-auth-helper`
- `JUKEBOX_SHUTDOWN_HELPER_COMMAND`
  Default install target: `/usr/local/libexec/jukebox-shutdown-helper`

Design notes:

- keeping helper command paths configurable makes tests easy without touching the host system
- the setup AP settings live in env because they are deployment-specific appliance config, not repo content
- the operator-state JSON must never include Spotify client secrets, refresh tokens, Wi-Fi passwords, or raw receiver credential files
- idle shutdown should be explicitly disabled by default on non-Pi local runs so development sessions do not self-terminate unexpectedly

## Feedback and Logging Design

`ControllerEvent` remains the canonical event bus, but EPIC 4 adds new event codes:

- `setup_required`
- `auth_required`
- `action_card_accepted`
- `action_succeeded`
- `action_failed`
- `playback_mode_changed`
- `volume_preset_applied`
- `shutdown_requested`
- `auto_shutdown_requested`

Terminal rendering expands accordingly:

- setup and auth-required modes become visible not-ready states
- queue-mode fallback from album or playlist to replace behavior becomes a distinct informative line
- shutdown and Wi-Fi reset become observable setup or system actions before the state transition occurs

Structured logs should add these fields when present:

- `card_kind`
- `action_name`
- `action_scope`
- `playback_mode`
- `setup_mode`
- `feedback_state`

The operator JSON status endpoint should expose:

- the current feedback snapshot
- scanner and playback readiness summary
- whether setup or auth-required mode is active
- the current playback mode
- the currently enabled action-card actions
- the non-secret runtime config relevant to maintenance
- idle-shutdown timer status

This is the JSON surface that [scripts/pi-smoke.sh](/Users/markus/Workspace/jukebox/scripts/pi-smoke.sh) should consume instead of re-implementing the health probe inline.

## Testing Strategy

The current test layout is already suitable for EPIC 4 if extended carefully.

### Unit Tests

- extend [tests/test_parser.py](/Users/markus/Workspace/jukebox/tests/test_parser.py) for `jukebox:` action-card parsing and unsupported-action handling
- extend [tests/test_controller.py](/Users/markus/Workspace/jukebox/tests/test_controller.py) for stop cards, next cards, queue-mode behavior, volume preset cards, Wi-Fi reset cards, receiver re-auth cards, shutdown cards, and duplicate handling across media versus actions
- extend [tests/test_feedback.py](/Users/markus/Workspace/jukebox/tests/test_feedback.py) for setup mode, auth-required mode, action rendering, and idle-shutdown rendering
- extend [tests/test_config.py](/Users/markus/Workspace/jukebox/tests/test_config.py) for the new operator HTTP, helper, setup AP, volume preset, and idle-shutdown settings
- extend [tests/test_main.py](/Users/markus/Workspace/jukebox/tests/test_main.py) so the operator server and idle monitor lifecycle are exercised alongside the health monitor
- extend [tests/test_playback_spotify.py](/Users/markus/Workspace/jukebox/tests/test_playback_spotify.py) for pause, next-track, queue-track, volume, and player-state behavior
- extend [tests/test_runtime_health.py](/Users/markus/Workspace/jukebox/tests/test_runtime_health.py) for `setup_required` and `auth_required`
- add `tests/test_operator_state.py` for JSON persistence and redaction behavior
- add `tests/test_operator_server.py` for HTML and JSON routes without touching real sockets or helpers
- add `tests/test_action_router.py` for action routing, debounce handling, playback-mode persistence, and helper failure mapping
- add `tests/test_idle_monitor.py` for idle timing and no-shutdown-while-playing behavior

### Script and Integration Tests

- update [scripts/pi-smoke.sh](/Users/markus/Workspace/jukebox/scripts/pi-smoke.sh) so it validates the service-owned JSON status surface and still supports the stdin replay path
- keep the one-shot stdin replay for media cards
- add a second smoke mode for action-card payload replay using `JUKEBOX_INPUT_BACKEND=stdin`
- add a smoke assertion that the JSON status surface reports setup or auth-required mode distinctly from `ready`

### Manual Pi Validation

EPIC 4 manual validation must add:

- real stop-card validation during playback
- next-track validation during active playback
- queue-mode validation for a track card and explicit fallback validation for album or playlist cards
- volume preset card validation against the external-speaker baseline
- shutdown-card validation
- Wi-Fi reset validation into setup fallback mode
- receiver re-auth card validation into the browser auth flow
- automatic setup AP fallback validation on a device with no usable Wi-Fi config
- idle auto-shutdown validation with documented recovery
- operator setup UI validation from another device
- JSON status endpoint validation for redacted config, current playback mode, and current action-card state

Because EPIC 4 explicitly touches networking, the full temporary network interruption test from [docs/pi-validation.md](/Users/markus/Workspace/jukebox/docs/pi-validation.md) must be rerun.

## Failure Handling

- Unknown `jukebox:` actions return `action_failed` with a reason such as `unsupported_action` instead of falling through as malformed Spotify URIs.
- Action cards pass through a debounce gate so one physical scan does not double-execute setup or shutdown behavior.
- Stop-card execution on a missing receiver returns the same underlying receiver or network reason codes already used by the Spotify backend.
- Next-track execution with no active playback context returns an explicit failure such as `no_active_playback`.
- Queue mode on album or playlist cards emits a specific informational fallback event and still uses replace dispatch.
- Volume preset failure returns a distinct reason such as `volume_control_unavailable` or `device_not_listed`.
- If the Wi-Fi helper is missing or exits nonzero, the action router surfaces a specific setup-action failure and leaves the device in its prior mode.
- If the shutdown helper fails, the runtime emits `action_failed` and continues in its prior state.
- If the operator-state JSON is missing or corrupt, the app recreates it from defaults, logs a reset event, and continues.
- If the `spotifyd` auth helper fails, the operator UI shows retryable failure state while the runtime remains in `auth_required` until recovery succeeds.
- If the operator HTTP server cannot bind its port, startup should fail in production mode because the companion interface is a selected EPIC 4 requirement.
- If player activity cannot be determined reliably, the idle monitor must fail safe by not auto-shutting down.

## Implementation Sequence

1. Introduce the new parsed-card model and generalize the controller for media versus action routing.
2. Extend the playback backend contract for stop, next, queue-track, volume preset, and player-state operations.
3. Implement the action router, action debounce gate, and persisted playback mode.
4. Add the feedback-state tracker and update terminal rendering and structured logs for setup, auth, action, and shutdown events.
5. Add the operator-state store plus the JSON status endpoint, then switch `pi-smoke.sh` to consume it.
6. Add the browser-based operator pages and the wrapped `spotifyd authenticate` flow.
7. Add Wi-Fi setup and reset helper integration, automatic setup fallback policy, and setup-required runtime state.
8. Add the idle monitor plus graceful shutdown helper integration.
9. Update the Pi docs, env example, service unit, helper installation, and validation flow.
10. After the polished standalone baseline is validated on the real appliance, run the post-standalone review checkpoint against the selected EPIC 4 control and feedback experiments before deciding any V2 physical-control or richer-feedback follow-up.

## Open Risks

- The setup AP implementation depends on the exact network stack present on the supported Raspberry Pi OS image. The helper boundary keeps that uncertainty contained, but the real image must be verified during implementation.
- `spotifyd authenticate` is an external CLI contract. Wrapping it is less risky than reimplementing receiver credentials, but it still needs a real Pi validation pass.
- Spotify software volume support may behave differently across receiver versions or output paths. Failure handling must stay honest so the external speaker remains the reliable baseline.
- Queue mode is intentionally limited to track cards. That is the right V1 compromise, but it may still need real-world explanation during the post-standalone review.
- Action cards such as Wi-Fi reset and shutdown are powerful. The design therefore treats them as explicit operator-only cards, debounces them, and keeps physical-control follow-up out of EPIC 4.
- Idle shutdown depends on correctly observing whether playback is still active. The design must fail safe toward staying on if that signal is uncertain.
