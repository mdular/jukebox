# EPIC 4 Technical Design

## Purpose

This document turns [spec/EPIC-4-requirements.md](/Users/markus/Workspace/jukebox/spec/EPIC-4-requirements.md) into an implementation design for the current Python repository.
It is intentionally scoped to EPIC 4: finish the standalone V1 appliance with clearer feedback, selected card-driven controls, companion setup and auth flows, automatic Wi-Fi fallback, and idle-power behavior while preserving the hardened EPIC 3 runtime.

This revision reconciles the design to three realities at once:

- the actual `main` branch already contains most of the EPIC 4 scaffolding
- the updated EPIC 4 requirements now make the Spotify playback behavior contract more explicit
- the strongest validated Spotify behavior currently lives across `fix-glitch-kilo-opus` and `playback-fix-codex`, not in `main` alone

The design therefore treats current `main` as the implementation baseline, carries forward the validated Spotify runtime changes from `fix-glitch-kilo-opus`, carries forward the probe tooling from `playback-fix-codex`, and leaves branch-only hardening that is not required by the updated requirements outside the default EPIC 4 design.

## Selected Decisions Carried Into This Design

This technical design assumes the checked decisions and notes in [spec/EPIC-4-requirements.md](/Users/markus/Workspace/jukebox/spec/EPIC-4-requirements.md):

- EPIC 4 promotes the existing runtime state model into a clearer user-facing feedback contract.
- Immediate acknowledgement remains distinct from playback confirmation, and the existing Netum NT-91 scanner beep is treated as part of that immediate acknowledgement rather than ignored.
- Stop behavior is card-driven first, not hardware-button driven.
- EPIC 4 reopens broader card-control design and includes the checked D-10 control items in V1 scope.
- Volume remains in the hardware audio path, and the mono amp-and-speaker baseline remains unchanged even though optional software-side volume preset cards are in scope.
- The operator flow expands into a browser-based companion configuration interface that can cover setup, receiver auth or re-auth, and selected recovery actions.
- Maintenance ergonomics stay focused and lightweight, including a diagnostic JSON surface rather than a full dashboard.
- EPIC 4 must preserve honest ready gating, honest replace-versus-queue behavior on the jukebox target, and explicit degraded-state visibility for receiver unavailability, controller-auth failure, network failure, and Spotify throttling.
- The checked D-10 items are committed EPIC 4 scope, while the unchecked items remain post-roadmap backlog.

This design makes five explicit implementation assumptions so the selected requirements stay concrete:

- The additional setup card selected under D-10 remains `setup.receiver-reauth`, because receiver auth and re-auth are already selected maintenance flows and the current repo already routes that action through operator state.
- Replace-versus-queue mode remains `replace` versus `queue_tracks`. Track cards queue only while playback is already active on the jukebox target. Album and playlist cards keep replace semantics in queue mode and surface that limitation honestly.
- Replace-mode track starts adopt the validated `fix-glitch-kilo-opus` behavior: `{"uris": [track]}` payloads plus direct-play-first handoff. This is an implementation choice, not a payload-format change visible to cards.
- Because replace and queue behavior have been tested most on the `fix-glitch-kilo-opus` line without new issues, EPIC 4 does not add `stop_after_track`, background stop monitoring, or snapshot-based stale-content confirmation as default runtime behavior.
- The probe script and runbook from `playback-fix-codex` are worth carrying forward, but they must be adapted to the selected EPIC 4 baseline rather than preserving branch-only stop-after-track behavior.

## Branch Learnings Adopted

### Adopt From `fix-glitch-kilo-opus`

- direct-play-first handoff with transfer fallback
- single-URI track starts for replace mode
- cached OAuth tokens
- passive cached `status()` and passive cached `player_active()`
- scan-scoped `current_player_active()` for queue-mode routing
- bounded boot-time device visibility retries in `probe()`
- explicit `spotify_rate_limited` state and `Retry-After` visibility
- warning-level logging and terminal rendering for degraded playback states
- `docs/api-discipline.md` as an implementation guardrail

### Adopt From `playback-fix-codex`

- `docs/spotify-connect-debug.md`
- `scripts/spotify_connect_probe.py`

### Do Not Adopt As Default EPIC 4 Behavior

- `PlaybackRequest.stop_after_track`
- background stop-monitor threads
- snapshot-delta playback confirmation as a required runtime safeguard

Those remain optional future hardening ideas if later validation on the merge target demonstrates a real failure that they prevent.

## Design Goals

- Keep ordinary Spotify music-card behavior simple and child-first.
- Preserve the existing EPIC 4 control-card, setup-mode, operator-state, and helper boundaries already present on `main`.
- Make runtime readiness honest: no `ready` until the appliance can autonomously scan and play.
- Keep periodic background Spotify API usage at zero. Health and status paths must read cached state only; the temporary idle bridge may make one explicit validation only after a complete idle interval expires.
- Keep queue-mode behavior honest for track cards without pretending album or playlist queue support exists.
- Surface degraded Spotify causes distinctly enough that operators do not have to infer them from ambiguous playback symptoms.
- Reuse the current standard-library operator server and helper-script boundaries instead of adding a heavier web or system-management stack.
- Keep the code runnable on non-Pi machines where practical and keep Pi-only behavior behind adapters and scripts.

## Non-Goals

- No built-in volume control, further amp or speaker integration, or enclosure-acoustics work.
- No physical stop button, rotary encoder, next-track button, or GPIO control surface in EPIC 4.
- No broader management dashboard or child-facing daily-use web UI.
- No queue support for album or playlist cards.
- No `stop_after_track`, single-track completion control, or snapshot-confirmation hardening in the default EPIC 4 runtime.
- No local playback fallback, printer-friendly card generation, OTA updates, read-only filesystem mode, or other post-roadmap backlog items.
- No reimplementation of `spotifyd authenticate` protocols inside Python.

## Current Baseline

Current `main` already contains most of the EPIC 4 scaffolding that the earlier technical draft described as future work:

- [src/jukebox/core/cards.py](/Users/markus/Workspace/jukebox/src/jukebox/core/cards.py) already defines typed Spotify media cards, `jukebox:` action cards, supported action ids, and persisted playback modes.
- [src/jukebox/core/controller.py](/Users/markus/Workspace/jukebox/src/jukebox/core/controller.py) already routes action cards through an action router and media cards through replace-versus-queue behavior.
- [src/jukebox/adapters/action_router.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/action_router.py) already handles stop, next, playback-mode toggles, volume presets, Wi-Fi reset, receiver re-auth, and shutdown actions.
- [src/jukebox/operator_state.py](/Users/markus/Workspace/jukebox/src/jukebox/operator_state.py), [src/jukebox/operator_server.py](/Users/markus/Workspace/jukebox/src/jukebox/operator_server.py), [src/jukebox/setup_mode.py](/Users/markus/Workspace/jukebox/src/jukebox/setup_mode.py), [src/jukebox/feedback_state.py](/Users/markus/Workspace/jukebox/src/jukebox/feedback_state.py), [src/jukebox/idle_monitor.py](/Users/markus/Workspace/jukebox/src/jukebox/idle_monitor.py), and [src/jukebox/adapters/system_helpers.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/system_helpers.py) already exist and define the operator surface, persisted state, setup mode policy, feedback snapshot, idle tracking, and helper boundaries.
- `scripts/runtime/` already contains Wi-Fi, `spotifyd` auth, and shutdown helper entrypoints, and `sudoers/jukebox-maintenance` already scopes privileged execution.
- [scripts/runtime/jukebox-wifi-helper.sh](/Users/markus/Workspace/jukebox/scripts/runtime/jukebox-wifi-helper.sh) already contains the rollback-safe client-trial structure for Wi-Fi replacement, including pending state, boot-aware rollback, and setup-AP activation.
- `tests/` already covers the action router, parser, controller, operator server, operator state, setup mode, idle monitor, runtime, and helper adapters.

The remaining mismatch is concentrated in Spotify playback behavior, diagnostics, and stale documentation:

- [src/jukebox/adapters/playback_spotify.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_spotify.py) on `main` still uses transfer-first handoff, album-context track payloads when lookup succeeds, live `status()` calls, live `player_active()` calls, and uncached token refreshes.
- [src/jukebox/core/models.py](/Users/markus/Workspace/jukebox/src/jukebox/core/models.py) on `main` does not yet expose `current_player_active()` on the playback protocol.
- [src/jukebox/core/controller.py](/Users/markus/Workspace/jukebox/src/jukebox/core/controller.py) on `main` still bases queue-mode routing on `player_active()`, which can misroute scans when target activity is stale or unknown.
- [src/jukebox/config.py](/Users/markus/Workspace/jukebox/src/jukebox/config.py) and [src/jukebox/runtime.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime.py) on `main` do not yet carry the bounded startup device-probe retry settings from `fix-glitch-kilo-opus`.
- [src/jukebox/runtime_health.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime_health.py), [src/jukebox/adapters/feedback.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/feedback.py), and [src/jukebox/logging.py](/Users/markus/Workspace/jukebox/src/jukebox/logging.py) on `main` do not yet surface `spotify_rate_limited` as a first-class degraded state.
- The helper script boundary already exists, but [scripts/runtime/jukebox-spotifyd-auth-helper.sh](/Users/markus/Workspace/jukebox/scripts/runtime/jukebox-spotifyd-auth-helper.sh) is still a stub and must be completed for the standalone auth flow to be real.
- `main` does not yet carry forward `docs/api-discipline.md`, `docs/spotify-connect-debug.md`, or `scripts/spotify_connect_probe.py`.

## Spec Alignment Notes

### Current Repo vs Older Draft

The old technical draft assumed EPIC 4 still needed new modules like `receiver_auth.py` and a fresh operator-state layer.
That is no longer true.
The current repo already has the operator server, state store, setup-mode manager, idle monitor, action router, and helper adapter.

Resolution:

- keep those existing modules as the implementation backbone
- remove the invented `receiver_auth.py` layer from the design
- complete receiver auth through the existing `OperatorHttpServer -> CommandSystemHelpers.start_auth() -> jukebox-spotifyd-auth-helper.sh` path

### Honest Queue Mode Requires Scan-Scoped Target Activity

The updated requirements say queue mode must start playback when the jukebox target is idle or another client is active, and only queue once the jukebox target is already playing.
Current `main` cannot guarantee that because its queue decision uses `player_active()`.

Resolution:

- adopt `PlaybackBackend.current_player_active()` from `fix-glitch-kilo-opus`
- keep `player_active()` as a passive cached diagnostic signal
- use `current_player_active()` on the scan path for queue-mode track cards and, temporarily, once after an idle deadline expires
- treat any result other than `True` as fallback to replace-style dispatch

### Honest Diagnostics Require Passive Status

The updated requirements now explicitly care about degraded-state visibility for receiver unavailability and Spotify throttling.
Current `main` still burns API budget in `status()` and `player_active()`, which undermines that goal.

Resolution:

- adopt the `fix-glitch-kilo-opus` passive-status discipline
- seed playback status once in `probe()`
- update cached playback status and cached player activity as side effects of real operations
- make health and operator status consumers read cached values only
- let the interim idle monitor validate activity once only after a complete idle interval, pending the transition-driven observer design in [spec/EPIC-5-draft.md](/Users/markus/Workspace/jukebox/spec/EPIC-5-draft.md)
- surface `spotify_rate_limited` distinctly in health, terminal feedback, logging, and `status.json`

### Replace-Mode Confirmation Boundary

`playback-fix-codex` preserved stronger snapshot-based confirmation logic, but the updated requirements do not require it, and the latest validation supplied by the user says replace and queue mode have not shown new issues.

Resolution:

- keep exact requested item or context matching as the strongest confirmation signal
- keep the `fix-glitch-kilo-opus` target-device-playing fallback as the default EPIC 4 runtime behavior
- do not bundle snapshot confirmation or stop-after-track mechanics into the EPIC 4 baseline
- preserve the probe tooling so any future replace-mode regression can be reproduced before runtime complexity is added

## Architecture

```text
stdin / evdev
  -> Controller
       -> parse_scan_payload()
            -> SpotifyMediaCard
            -> JukeboxActionCard
       -> media card:
            -> DuplicateGate
            -> OperatorStateStore.load().playback_mode
            -> queue_tracks + track:
                 -> PlaybackBackend.current_player_active()
                 -> True     -> enqueue()
                 -> not True -> emit playback_mode_fallback -> dispatch()
            -> queue_tracks + album/playlist:
                 -> emit playback_mode_fallback -> dispatch()
            -> replace:
                 -> dispatch()
       -> action card:
            -> ActionDebounceGate
            -> ActionRouter.execute()
                 -> stop / next / volume
                 -> set playback mode
                 -> mark setup or auth required
                 -> request shutdown
       -> ControllerEvent stream

ControllerEvent stream
  -> TerminalStatusSink
  -> StructuredEventLogger
  -> FeedbackStateTracker
  -> IdleMonitor

Runtime services
  -> RuntimeHealthMonitor
       -> scanner status
       -> passive playback status
       -> setup mode status
  -> OperatorHttpServer
       -> GET /
       -> GET /status.json
       -> GET/POST /wifi
       -> GET /auth
       -> POST /auth/start
  -> SetupModeManager
       -> reads OperatorStateStore
       -> uses wifi helper status
       -> controls setup-required and auth-required readiness

SpotifyPlaybackBackend
  -> probe() seeds passive status cache and device visibility state
  -> dispatch():
       -> refresh cached token if needed
       -> resolve target device
       -> direct play first
       -> transfer fallback only if needed
       -> confirm playback on configured target
       -> update passive status + player_active cache
  -> current_player_active():
       -> one explicit /me/player read for queue routing
       -> temporary one-read validation after an expired idle interval
  -> status(), player_active():
       -> no API calls

Helper scripts
  -> jukebox-wifi-helper.sh
  -> jukebox-spotifyd-auth-helper.sh
  -> jukebox-shutdown-helper.sh

Diagnostics
  -> docs/api-discipline.md
  -> docs/spotify-connect-debug.md
  -> scripts/spotify_connect_probe.py
```

The controller, operator-state layer, setup-mode layer, and helper boundaries already present on `main` remain the core structure.
The main architectural change is to bring the Spotify backend and its consumers in line with the passive-status and validated replace-versus-queue behavior from `fix-glitch-kilo-opus`.

## Runtime Flow

### Normal Boot

1. `systemd` starts `jukebox.service` as `pi`.
2. [src/jukebox/main.py](/Users/markus/Workspace/jukebox/src/jukebox/main.py) loads config, configures logging, emits `booting`, and calls `build_runtime()`.
3. [src/jukebox/runtime.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime.py) builds the input adapter, playback backend, operator state store, feedback tracker, setup-mode manager, action router, idle monitor, operator server, and health monitor.
4. `build_runtime()` immediately calls `playback_backend.probe()` before starting background services.
5. `probe()` must:
   - validate controller-side Spotify auth
   - seed the passive playback status cache
   - retry target-device lookup for a bounded startup window when the target is temporarily `device_not_listed`
6. If controller auth fails, startup raises `StartupError` and the service fails observably.
7. If auth succeeds but the receiver is still not visible after the bounded retry window, startup continues in degraded `receiver_unavailable` rather than failing the process.
8. The operator server starts before normal scan processing so `/status.json` and setup/auth surfaces remain available during recovery.
9. `SetupModeManager.initialize()` decides whether the box is in normal client mode, setup-required mode, or auth-required mode.
10. `RuntimeHealthMonitor` emits `ready` only when scanner, playback, and setup/auth status are all ready.

### Media Card Handling

1. The controller receives one newline-terminated payload from `stdin` or `evdev`.
2. `parse_scan_payload()` returns either a `SpotifyMediaCard` or a `JukeboxActionCard`.
3. For media cards, duplicate suppression stays unchanged from earlier EPICs.
4. The controller reads `playback_mode` from `OperatorStateStore`.
5. In `replace` mode:
   - track cards call `dispatch()` with the validated direct-play-first path
   - album and playlist cards call `dispatch()` with context playback
6. In `queue_tracks` mode:
   - track cards call `current_player_active()`
   - if that returns `True`, the controller calls `enqueue()`
   - if that returns `False` or `None`, the controller emits `playback_mode_fallback` and calls `dispatch()` instead
   - album and playlist cards always emit `playback_mode_fallback` and use `dispatch()`
7. Track-card dispatch uses the `fix-glitch-kilo-opus` replace-mode semantics:
   - `{"uris": [track]}` payload for track starts
   - direct `/play?device_id=...` first
   - explicit transfer fallback only when direct play fails
8. Playback confirmation behavior is:
   - exact requested item or context match when Spotify reports it in time
   - otherwise success only when the configured jukebox target is playing
   - never treat playback on another client as success
9. Successful playback or enqueue operations update duplicate state only after backend confirmation succeeds.

### Action Card Handling

1. Action cards continue through `ActionDebounceGate` and `ActionRouter`.
2. `ActionRouter` remains the single Python boundary for:
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
3. Child-facing actions remain playback and mode actions.
4. Operator-facing actions remain setup and shutdown actions.
5. Unsupported or disabled `jukebox:` actions must fail as distinct `unsupported_action` outcomes.

### Setup, Auth, and Operator Surface

1. `OperatorHttpServer` remains a lightweight standard-library server.
2. It continues to expose:
   - browser-readable operator landing page
   - `GET /status.json`
   - `GET` and `POST /wifi`
   - `GET /auth`
   - `POST /auth/start`
3. The JSON status surface remains the source of truth for:
   - `feedback`
   - runtime playback mode
   - setup-required and auth-required flags
   - enabled action ids
   - scanner, playback, setup, and idle status
   - non-secret maintenance config
4. Receiver auth remains implemented through the existing helper boundary, but the helper script must be completed so `POST /auth/start` returns a real approval flow rather than the current stub failure.
   - browser-initiated auth marks receiver re-auth as requested before starting the helper
   - persisted state distinguishes a requested flow from one that has actually started
   - only success from the current started flow clears `auth_required`; stale helper success does not
   - helper unavailability remains an auth degradation and does not block unrelated runtime startup
5. Wi-Fi replacement remains implemented through the existing helper boundary:
   - the operator server submits SSID and passphrase to `CommandSystemHelpers.apply_wifi()`
   - the Wi-Fi helper snapshots the previous working client connection when one exists
   - the helper arms a rollback timer that survives Python-process exit and ordinary client connectivity loss
   - if setup is not confirmed in time or the device reboots with a pending trial, the helper restores the prior working client configuration automatically

### Idle and Health Monitoring

1. `IdleMonitor` continues to derive household activity from controller events and remain disabled during `setup_required` and `auth_required`.
2. As an interim EPIC 4 bridge, `IdleMonitor` may call `current_player_active()` once only after a complete idle interval expires; active or unknown state re-arms another complete interval, while confirmed inactivity requests shutdown.
3. Ordinary idle ticks must not call Spotify. The bridge is marked `TODO(EPIC-5)` and must be replaced by playback-state transitions from a backend-neutral observer.
4. `RuntimeHealthMonitor` must read passive playback status only and never trigger Spotify API calls indirectly.
5. Health priority must treat `spotify_rate_limited` as a degraded state distinct from generic network failure.

## Module Plan

### Existing Files to Extend

- [src/jukebox/adapters/playback_spotify.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_spotify.py)
  Purpose: adopt direct-play-first handoff, single-URI track starts, cached tokens, passive `status()` and `player_active()`, explicit `current_player_active()` validation, bounded startup device retries, and explicit `spotify_rate_limited` handling.
- [src/jukebox/core/models.py](/Users/markus/Workspace/jukebox/src/jukebox/core/models.py)
  Purpose: formalize `status()` and `current_player_active()` on the `PlaybackBackend` protocol and keep `PlaybackRequest` free of branch-only `stop_after_track` behavior.
- [src/jukebox/core/controller.py](/Users/markus/Workspace/jukebox/src/jukebox/core/controller.py)
  Purpose: use `current_player_active()` for queue-mode track routing and treat any result other than `True` as fallback to `dispatch()`.
- [src/jukebox/config.py](/Users/markus/Workspace/jukebox/src/jukebox/config.py)
  Purpose: add bounded device-probe retry settings and adopt the longer health poll default used by the passive-status design.
- [src/jukebox/runtime.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime.py)
  Purpose: call `probe()` during startup, pass the new retry settings into the backend, and keep the runtime status JSON built from passive sources.
- [src/jukebox/runtime_health.py](/Users/markus/Workspace/jukebox/src/jukebox/runtime_health.py)
  Purpose: add `spotify_rate_limited` to the degraded-state priority ladder.
- [src/jukebox/adapters/feedback.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/feedback.py)
  Purpose: render a distinct terminal line for rate limiting and keep ready/degraded signals honest.
- [src/jukebox/logging.py](/Users/markus/Workspace/jukebox/src/jukebox/logging.py)
  Purpose: log degraded runtime events at warning level and include `spotify_rate_limited`.
- [src/jukebox/adapters/playback_stub.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_stub.py)
  Purpose: satisfy the extended playback protocol without introducing Spotify-specific behavior.
- [tests/test_playback_spotify.py](/Users/markus/Workspace/jukebox/tests/test_playback_spotify.py)
  Purpose: carry forward the validated `fix-glitch-kilo-opus` behavior around direct play, token caching, passive status, current-player checks, bounded probe retries, and 429 handling.
- [tests/test_controller.py](/Users/markus/Workspace/jukebox/tests/test_controller.py)
  Purpose: lock in the queue-mode routing rule that only `True` means "already active on the jukebox target."
- [tests/test_runtime_health.py](/Users/markus/Workspace/jukebox/tests/test_runtime_health.py), [tests/test_feedback.py](/Users/markus/Workspace/jukebox/tests/test_feedback.py), and [tests/test_logging.py](/Users/markus/Workspace/jukebox/tests/test_logging.py)
  Purpose: lock in `spotify_rate_limited` as a first-class degraded state.
- [README.md](/Users/markus/Workspace/jukebox/README.md), [docs/pi-setup.md](/Users/markus/Workspace/jukebox/docs/pi-setup.md), [docs/pi-validation.md](/Users/markus/Workspace/jukebox/docs/pi-validation.md), and [systemd/jukebox.env.example](/Users/markus/Workspace/jukebox/systemd/jukebox.env.example)
  Purpose: align the operator workflow, playback expectations, probe settings, and troubleshooting guidance to the selected runtime behavior.
- [scripts/runtime/jukebox-spotifyd-auth-helper.sh](/Users/markus/Workspace/jukebox/scripts/runtime/jukebox-spotifyd-auth-helper.sh)
  Purpose: replace the current placeholder with a real wrapped `spotifyd authenticate` flow that fits the operator server contract.

### Files to Add

- `docs/api-discipline.md`
  Purpose: carry forward the API-call-budget rules from `fix-glitch-kilo-opus`.
- `docs/spotify-connect-debug.md`
  Purpose: carry forward the probe-first debugging runbook from `playback-fix-codex`, updated for the selected EPIC 4 baseline.
- `scripts/spotify_connect_probe.py`
  Purpose: carry forward the Spotify handoff probe script from `playback-fix-codex`, updated to reflect direct-play-first and the selected payload policy.

No new Python architecture layer is required for auth or diagnostics beyond those additions.

## Data Model

### Parsed Cards

The current parsed-card model on `main` already matches EPIC 4:

- `SpotifyMediaCard`
  Fields: `raw`, `kind`, `spotify_id`
- `JukeboxActionCard`
  Fields: `raw`, `group`, `action`, `action_id`

The action-card namespace remains `jukebox:<group>:<action>`.

### Playback Request and Backend Contract

`PlaybackRequest` remains intentionally small:

- `uri`

EPIC 4 does not add `stop_after_track`.

The playback backend contract becomes:

- `probe()`
- `status()`
- `dispatch()`
- `enqueue()`
- `stop()`
- `skip_next()`
- `set_volume_percent()`
- `player_active()` for passive background reads
- `current_player_active()` for explicit queue routing and the temporary expired-idle-deadline bridge

### Operator State

The persisted operator state includes:

- `playback_mode`
- `setup_requested`
- `receiver_reauth_requested`
- `receiver_reauth_started`
- `last_wifi_mode`
- `enabled_actions`
- `schema_version`

No secrets belong in that JSON file.

### Feedback Snapshot

The shared feedback snapshot remains the current repo design, with one addition:

- support explicit `spotify_rate_limited` display state alongside `ready`, `setup_required`, `auth_required`, `receiver_unavailable`, and `network_unavailable`

## Configuration Design

EPIC 4 keeps the current env-file model and helper-command boundaries.
The main additions are the validated Spotify probe settings:

- `JUKEBOX_SPOTIFY_DEVICE_PROBE_RETRY_COUNT`
  Default: `5`
- `JUKEBOX_SPOTIFY_DEVICE_PROBE_RETRY_INTERVAL_SECONDS`
  Default: `2.0`

Existing settings remain in place for:

- confirmation timeout and poll interval
- operator HTTP bind and port
- operator-state path
- control debounce
- playback-mode default
- volume preset percentages
- idle shutdown
- setup AP configuration
- Wi-Fi rollback timeout
- helper command paths

Design notes:

- `JUKEBOX_HEALTH_POLL_INTERVAL_SECONDS` should move from the current `5.0` default to `15.0` to match the passive-status design and avoid unnecessary churn.
- Background poll interval tuning no longer carries Spotify API risk once playback status is passive, but the slower default keeps logs and state churn calmer on a Pi 3.
- No setting is added for snapshot confirmation or stop-after-track because those are not baseline EPIC 4 behavior.

## Feedback and Logging Design

`ControllerEvent` remains the canonical event bus.
The key runtime additions are not new event families, but sharper degraded-state rendering:

- `spotify_rate_limited` must render distinctly in terminal feedback
- degraded events must be logged at warning level, not informational level
- `status.json` must expose `runtime.playback.code = spotify_rate_limited` when relevant

The selected operator and diagnostic surfaces become:

- terminal feedback for immediate operator visibility
- structured JSON logs for diagnosis
- `GET /status.json` for service-owned runtime state
- `docs/api-discipline.md` for design guardrails
- `docs/spotify-connect-debug.md` plus `scripts/spotify_connect_probe.py` for investigation when Spotify UI state and device behavior diverge

## Testing Strategy

### Unit Tests

- carry forward the `fix-glitch-kilo-opus` Spotify backend tests for:
  - token caching
  - passive `status()`
  - passive `player_active()`
  - explicit `current_player_active()`
  - direct-play-first with transfer fallback
  - single-URI track starts
  - bounded probe retries
  - `spotify_rate_limited` plus `Retry-After` rendering
- update controller tests so queue-mode routing only enqueues on `current_player_active() is True`
- update runtime-health, feedback, and logging tests to cover `spotify_rate_limited`
- extend runtime tests to cover startup `probe()` seeding and the new retry settings
- extend idle-monitor tests to prove that the temporary live validation happens only after a full interval and re-arms a full interval for active or unknown state
- keep operator-server, setup-mode, and action-router tests as the current scaffold; they already match the selected architecture

### Script and Integration Tests

- update `scripts/pi-smoke.sh` expectations around the service-owned `status.json` surface and degraded playback codes
- add repository coverage for `scripts/spotify_connect_probe.py`
- keep the existing helper-script tests and extend them only as needed for the completed auth helper

### Manual Pi Validation

Manual Pi validation should now treat replace and queue mode as the primary playback regression matrix because those paths have the strongest recent validation:

- replace-mode track starts after stale context elsewhere
- queue-mode first scan while another client is active
- queue-mode later scans during active jukebox playback
- bounded startup receiver visibility recovery after boot
- degraded recovery and `spotify_rate_limited` visibility

The stale stop-after-track expectation currently present in `docs/pi-validation.md` should be removed as part of this alignment work.

## Failure Handling

- If controller-side Spotify auth fails during startup `probe()`, startup fails observably with `controller_auth_unavailable`.
- If the receiver is not yet visible during startup, the backend seeds `receiver_unavailable` and the process still starts.
- If the startup retry window expires without receiver visibility, the runtime remains degraded until a later successful user action or recovery.
- If `current_player_active()` cannot prove the jukebox target is already active, queue mode falls back to `dispatch()` instead of silently enqueuing.
- If Spotify returns HTTP 429, the runtime maps it to `spotify_rate_limited`, logs at warning level, and does not hide it under generic network failure.
- If `Retry-After` is present, surface it in the message; do not build automatic background recovery polling around it.
- If exact playback metadata stays stale but the configured target device is clearly playing, the selected EPIC 4 baseline still treats that as success.
- If future validation demonstrates that this permissive confirmation is wrong on the merge target, diagnose it with the probe tooling before adding snapshot or completion-time runtime complexity.
- If a Wi-Fi replacement or reset trial times out before the new path is confirmed, the existing Wi-Fi helper restores the prior working client configuration automatically.
- If the device reboots while a Wi-Fi trial is still pending, the helper resolves that conservatively by restoring the prior working client configuration unless the new configuration was already committed.
- If the auth helper remains stubbed or fails, the operator surface remains in `auth_required` and the appliance does not claim `ready`.

## Implementation Sequence

1. Update the playback backend contract and carry forward the `fix-glitch-kilo-opus` Spotify runtime changes into `main`.
2. Update controller queue-mode routing to use `current_player_active()` and fallback on any non-`True` result.
3. Wire the new probe retry settings through config and runtime startup.
4. Update runtime health, terminal feedback, and structured logging for `spotify_rate_limited`.
5. Carry forward `docs/api-discipline.md`.
6. Carry forward `docs/spotify-connect-debug.md` and `scripts/spotify_connect_probe.py`, adapted to the selected EPIC 4 baseline.
7. Complete the `spotifyd` auth helper so the existing operator-server contract becomes a real standalone flow.
8. Align Pi setup, validation, and env-template docs to the new behavior contract.

## Implementation Progress

- [x] Batch 1: playback backend contract, passive status caching, queue-mode routing, and playback tests
- [x] Batch 2: auth helper, operator auth surface, and auth-path tests
- [x] Batch 3: runtime startup probing, config wiring, and degraded observability updates
- [x] Batch 4: diagnostics tooling, docs alignment, and smoke-test updates

## Open Risks

- The exact startup retry window may need tuning on real Pi hardware and Spotify-side propagation timing.
- The selected confirmation fallback remains more permissive than `playback-fix-codex` snapshot confirmation. That is acceptable for EPIC 4 only because recent replace and queue validation has not surfaced new issues.
- Queue mode remains intentionally limited to track cards. That is the right EPIC 4 compromise, but it still needs explicit documentation and validation coverage.
- The current auth helper is still incomplete. That is now the main gap in the standalone maintenance surface.
- Diagnostic tooling is only useful if it stays in the active branch. Once restored, it should be treated as part of the supported troubleshooting workflow, not as disposable branch-local debugging residue.
