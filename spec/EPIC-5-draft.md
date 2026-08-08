# EPIC 5 Draft: Unified Appliance State and Effects

## Status

This is a provisional post-EPIC-4 proposal prompted by an operational idle-shutdown failure.
It is not yet part of the four-EPIC roadmap and does not replace the V2 audio and controls direction in [spec/concept.md](/Users/markus/Workspace/jukebox/spec/concept.md).
The draft deliberately records both a minimal useful architecture and possible later extensions so scope can be reduced during review before requirements or implementation are committed.

## Motivation

The current runtime can successfully request playback without learning when playback later ends.
The Spotify command adapter caches player activity as a side effect of commands, while idle shutdown separately tracks a last-activity timestamp from controller events.
When a queue, playlist, album, or directly played item ends naturally, neither value is guaranteed to change.
In operation this allowed the idle deadline to pass without shutdown; a later card scan refreshed player activity and exposed the already-idle condition.

This is a design problem rather than a Spotify-specific timeout problem.
Local media playback must produce the same lifecycle behavior without duplicating idle policy inside each backend.

## Current Implementation Gap

The current runtime has no formal playback state machine and no single appliance-runtime state authority.
Despite its name, `SpotifyPlaybackBackend` is not a `spotifyd` lifecycle adapter.
It sends commands through Spotify's Web API and returns a synchronous result that answers questions such as:

- Was the play request accepted?
- Could playback be confirmed as started?
- Did pause, enqueue, next, or volume control succeed?

The call finishes shortly after the command is handled.
It does not return a session handle or a later completion result when a track, queue, album, or playlist ends.
`spotifyd` runs independently, and the Python runtime currently receives no lifecycle events from it.

Playback-related state is therefore fragmented across:

- `_cached_player_active` in `SpotifyPlaybackBackend`
- `_cached_status` for dependency readiness
- `_last_activity` and setup flags in `IdleMonitor`
- controller events consumed independently by feedback and idle handling
- live player-state reads performed only on selected code paths

No transition function enforces a coherent relationship between those values.
The passive cache reduced Spotify API polling, but without a producer for natural-completion events it is not a playback-state authority.

The same pattern exists outside playback:

- `OperatorStateStore` contains durable preferences alongside setup and receiver-auth workflow flags.
- `SetupModeManager.status()` derives runtime mode by rereading persisted flags and calling the Wi-Fi helper.
- `RuntimeHealthMonitor` polls several dependencies and collapses simultaneous failures to one code using a priority table.
- `FeedbackStateTracker` treats the most recently received `ControllerEvent` as the current display state, regardless of other still-active conditions.
- `IdleMonitor` independently interprets controller events and carries its own setup-mode flag.
- Wi-Fi reset, receiver re-auth, and shutdown perform side effects directly in action or HTTP handlers, then update other state separately.
- Several background threads can publish string-coded events to consumers that maintain their own snapshots.

These are manageable in isolation, but together they mean setup, readiness, feedback, idle policy, and persisted intent can disagree without one authority rejecting an invalid transition.

## Current Spotify and `spotifyd` Topology

The repository currently has two separate Spotify-facing identities and control paths:

```text
Python jukebox controller
  -> controller client id + secret + refresh token
  -> Spotify Accounts token endpoint
  -> Spotify Web API playback commands and state reads
  -> targets the Connect device advertised by spotifyd

spotifyd receiver process
  -> receiver-side OAuth/session credentials
  -> Spotify Connect session
  -> local ALSA audio output

systemd
  -> starts, stops, restarts, and supervises spotifyd.service
```

The Python process does not currently send commands to the local `spotifyd` process.
It asks Spotify's Web API to control a Connect device, and `spotifyd` acts as the independently connected client speaker that receives and renders that stream.

### Controller Credentials

The Python controller reads `JUKEBOX_SPOTIFY_CLIENT_ID`, `JUKEBOX_SPOTIFY_CLIENT_SECRET`, and `JUKEBOX_SPOTIFY_REFRESH_TOKEN` from `/etc/jukebox/jukebox.env`.
It exchanges the refresh token for cached access tokens and uses the Web API scopes `user-read-playback-state` and `user-modify-playback-state`.
Those credentials authorize remote playback control; they do not authenticate the local receiver process.

### Receiver Credentials and Service Lifecycle

`spotifyd` reads `/etc/spotifyd.conf`, including the persistent `cache_path` currently documented as `/var/cache/spotifyd`.
The upstream OAuth flow stores receiver credentials at `<cache_path>/oauth/credentials.json`.
The repository's `jukebox-spotifyd-auth-helper.sh` invokes `spotifyd authenticate`, records pending/running/succeeded/failed helper state under `/var/lib/jukebox/spotifyd-auth-helper`, and surfaces the browser approval URL.

The helper does not currently call `systemctl`, stop the running receiver, or restart it after authentication.
Service lifecycle is separately owned by systemd and by deployment or operator commands outside the Python runtime.
Therefore the current receiver flow is credential-file bootstrap plus independently managed service supervision, not a single coordinated auth-and-lifecycle workflow.

EPIC 5 should make that boundary explicit rather than assume the Python playback adapter owns `spotifyd`.
An early validation increment must determine whether the deployed version notices newly written credentials while running or requires a controlled restart, and which local interface can provide reliable receiver lifecycle and playback observations.
The helper should gain service-control responsibility only if that validation proves it necessary; routine supervision should remain with systemd.
The appliance snapshot must contain only sanitized auth workflow and service status; client secrets, refresh tokens, receiver credential contents, and other session material remain exclusively in their protected configuration or cache boundaries.

## Objective

Introduce one core appliance-state authority that owns runtime truth for appliance lifecycle, operating mode, playback lifecycle, connectivity, dependency readiness, active maintenance operations, and recoverable issues.
Playback is the first vertical slice because it exposes the operational bug, but it must fit the same authority later used by setup, Wi-Fi reset, receiver authentication, feedback, health, and shutdown.
The same state model and component boundaries should permit a future alternate streaming service or local-media backend without replacing appliance policy.
EPIC 5 does not need to ship real backend selection, fallback, or local-media functionality; portability is a design objective and contract test, not a feature commitment.

## Design Principles

- The appliance has one authoritative immutable snapshot and one serialized transition path.
- The snapshot is composite, not one flat enum whose states encode every cross-product of playback, setup, connectivity, and errors.
- Small domain reducers may exist as pure implementation functions, but they do not run independently or own parallel snapshots.
- Typed inputs describe facts that happened; a root transition function is the only path that changes runtime state.
- Side effects do not occur inside the reducer. The reducer returns explicit effects, and adapters return their outcomes as new inputs.
- Command acceptance and observed lifecycle state are different facts.
- Playback command adapters expose commands; playback observers report lifecycle evidence.
- Core appliance and playback types do not encode Spotify, `spotifyd`, OAuth, or local-player-specific states.
- Every selected playback backend maps its own readiness, setup needs, command outcomes, and lifecycle observations into the same core contract.
- A backend that needs no authentication or setup reports setup as not required and ready; it does not cause a different appliance state model.
- Backend unavailability is explicit and cannot be mistaken for idle playback.
- Recoverable issues can coexist with useful activity instead of replacing all state with a generic `error` state.
- Feedback, logs, health, operator status, and policy decisions are projections of the authoritative snapshot or its transitions.
- Durable preferences and necessary reboot-recovery checkpoints are persisted separately from volatile runtime truth.
- Ordinary observation must not depend on periodic provider API polling.
- Unknown or lost observation must fail conservatively and must not cause an unsafe shutdown.
- The initial implementation should use standard-library data structures and synchronization rather than a state-machine framework.

## Proposed State Model

The exact types and names remain review decisions.
The smallest credible composite snapshot is:

```text
ApplianceState
  generation
  lifecycle
    booting | running | shutting_down | faulted
  operating_mode
    normal | wifi_setup | playback_backend_setup
  playback_backend
    id
    readiness
      unknown | ready | setup_required | unavailable
    setup
      unknown | not_required | required | in_progress | succeeded | failed
    service
      unknown | not_applicable | available | unavailable
  playback
    activity
      unknown | idle | starting | playing | paused
    observation
      unknown | available | unavailable
    item identity, when known
    transition generation and time
  connectivity
    unknown | connected | reconfiguring | setup_ap | unavailable
  dependencies
    scanner status
    selected playback-backend status
    selected playback-observer status
    other keyed appliance dependency statuses
  active_operation
    none | wifi_reset | playback_backend_setup | shutdown
  issues
    zero or more typed recoverable issues
```

`faulted` is reserved for an appliance-level condition that prevents useful operation and cannot presently recover.
Ordinary scanner, network, receiver, auth, or rate-limit failures belong in typed dependency state or `issues` so they can coexist and recover independently.

Playback availability is deliberately separate from playback activity.
For example, losing observation while a track may still be playing transitions observation to `unavailable` and activity to `unknown`; it must not manufacture `idle`.
An operator-facing projection may still render an effective `receiver_unavailable` state without flattening the authoritative snapshot.

Backend setup is normalized in the same way.
The current Spotify path can report that receiver authorization is required and map its helper progress into `required`, `in_progress`, `succeeded`, or `failed` outcomes.
A local-media backend with no authentication reports `not_required` and ready immediately.
Neither case changes the shape or transition rules of `ApplianceState`.

Persisted `playback_mode`, enabled actions, and other operator preferences are configuration inputs, not volatile appliance state.
Wi-Fi or playback-backend setup intent should be persisted only where it is required to resume or roll back a workflow safely across process restart or power loss.

### Candidate Typed Inputs

The event set should grow only as each increment needs it.
Candidate inputs include:

- appliance lifecycle: `BOOT_COMPLETED`, `SHUTDOWN_REQUESTED`, `SHUTDOWN_FAILED`
- playback commands: `PLAY_REQUESTED`, `PLAY_COMMAND_ACCEPTED`, `PLAY_COMMAND_FAILED`, `PAUSE_COMMAND_ACCEPTED`
- playback observations: `PLAYBACK_STARTED`, `TRACK_CHANGED`, `PLAYBACK_PAUSED`, `PLAYBACK_ENDED`, `OBSERVATION_LOST`, `OBSERVATION_RESTORED`
- connectivity and setup: `WIFI_RESET_REQUESTED`, `WIFI_RECONFIGURATION_STARTED`, `WIFI_CONNECTED`, `SETUP_AP_STARTED`, `WIFI_OPERATION_FAILED`
- backend setup and service: `BACKEND_SETUP_REQUESTED`, `BACKEND_SETUP_STARTED`, `BACKEND_SETUP_SUCCEEDED`, `BACKEND_SETUP_FAILED`, `BACKEND_SERVICE_CHANGED`
- dependency health: `SCANNER_STATUS_CHANGED`, `PLAYBACK_BACKEND_STATUS_CHANGED`, `PLAYBACK_OBSERVER_STATUS_CHANGED`
- time-based policy: `IDLE_TIMEOUT_ELAPSED` carrying the idle-state generation it was armed for

Names in this list are illustrative, not a commitment to a large class hierarchy.
A typed dataclass with an enum discriminator and a small payload may be enough.

### Usage Scenario Matrix

The composite shape exists because these facts are not always mutually exclusive:

| Scenario | Lifecycle | Mode | Playback | Connectivity or dependency fact | Active operation | Policy consequence |
|---|---|---|---|---|---|---|
| Booting | `booting` | — | `unknown` | dependencies still resolving | none | no idle timer; readiness is not yet claimed |
| Ready and waiting | `running` | `normal` | confirmed `idle` | required dependencies ready | none | arm idle timer |
| Playing while Web API is rate-limited | `running` | `normal` | observed `playing` | controller issue active | none | keep playback fact; show degradation; no idle timer |
| Wi-Fi reset | `running` | `wifi_setup` | observed or `unknown` | connectivity `reconfiguring` | `wifi_reset` | suppress idle timer and reject stale Wi-Fi results |
| Spotify receiver authentication | `running` | `playback_backend_setup` | `unknown` with observation unavailable | selected backend setup pending | `playback_backend_setup` | suppress idle timer; surface approval or failure state |
| Local backend with no auth | `running` | `normal` | `idle` or observed activity | backend setup `not_required` | none | use the same playback and idle policies |
| Natural playback completion | `running` | `normal` | `playing` to confirmed `idle` | observer available | none | arm timer for the new idle generation |
| Shutdown | `shutting_down` | — | preserved for diagnostics | dependencies may disappear | `shutdown` | reject new playback and maintenance work |

The values are examples for design review.
They demonstrate why one flat appliance enum would grow into combinations such as `PLAYING_WITH_CONTROLLER_RATE_LIMITED`, while independent state authorities would make cross-domain policy difficult to enforce.

## Backend Portability Objective

EPIC 5 should leave the appliance able to select one configured playback backend whose implementation may be Spotify Connect, another streaming service, or local media.
The core does not need to operate several backends concurrently.

At the design level, every backend is expected to provide the same normalized responsibilities:

- identify itself for diagnostics
- report readiness as unknown, ready, setup required, or unavailable
- report setup progress using the shared not-required, required, in-progress, succeeded, or failed semantics
- execute the playback commands included in the selected core contract and return normalized accepted, failed, or unsupported outcomes
- publish backend-neutral playback observations such as started, item changed, paused, ended, or observation lost
- expose sanitized dependency details without leaking provider credentials or changing core policy types

The exact Python protocol should be extracted from the first two proven shapes rather than designed in the abstract.
For EPIC 5 those shapes can be the real Spotify command/receiver path and a deterministic process-backed local-media test adapter.
The latter proves no-auth setup and natural process completion without committing to media-library discovery, metadata, or a supported local playback product.
It must implement the same preparation, command-result, and observation boundaries rather than bypassing the appliance state machine as a test shortcut.

### Setup and Authentication Normalization

Authentication is a possible backend setup mechanism, not an appliance-wide assumption.
A common readiness or preparation contract can return a normalized result:

- Spotify receiver credentials missing: setup required, with an adapter-owned authorization effect
- Spotify receiver credentials usable: ready
- local player requiring no credentials: ready with setup not required
- future service requiring a different setup flow: setup required, translated by that adapter

The root reducer responds to normalized setup facts and effect outcomes.
It does not contain provider-specific OAuth transitions or a separate local-media state model.
Provider-specific details such as an approval URL remain in the adapter/effect boundary and sanitized projections.

The exact API does not need to force meaningless work.
For example, a no-auth backend may return ready or not-required immediately from the common preparation call; the runtime should not start a setup effect after that result.

### Premature-Abstraction Guardrails

- Do not add plugin discovery, dynamic loading, or a backend registry merely to satisfy this objective.
- Do not build runtime backend switching, simultaneous playback, automatic fallback, or cross-backend queue migration in EPIC 5.
- Do not create a generic OAuth or browser-flow engine; keep the current receiver flow adapter-specific until a second real flow proves a shared abstraction.
- Do not add a large capability matrix up front. Where possible, a normalized `unsupported` command result is simpler; add an explicit capability only when policy must know before issuing a command.
- Do not normalize provider metadata that no current policy consumes.
- Do not require every backend to have a service process, network dependency, auth flow, queue, volume control, or item metadata. Use shared not-applicable, not-required, unknown, or unsupported outcomes where the distinction matters.
- Do not let a test adapter dictate product functionality. It exists to prove the core boundary and lifecycle behavior.
- Do require state-machine and policy tests to run without Spotify-specific types or credentials.

## Proposed Architecture

```text
scanner, HTTP, timers, dependency monitors,
playback command results, playback observations
                         |
                         v
                 serialized input path
                         |
                         v
        reduce(ApplianceState, ApplianceInput)
                         |
               +---------+---------+
               |                   |
               v                   v
       new ApplianceState     requested effects
               |                   |
       +-------+-------+       effect adapters
       |       |       |            |
       v       v       v            +--> outcome inputs
   feedback  status   logs
```

The root reducer should be a pure function from the previous snapshot and one input to a transition result containing the next snapshot and zero or more requested effects.
A small store serializes calls from the scanner loop, operator HTTP thread, health monitor, playback observer, and timers.
The store may initially be a lock-protected synchronous dispatcher or a small standard-library queue; the concurrency choice is a review item, not a reason to introduce a framework.

Domain logic may be split into functions such as `reduce_playback`, `reduce_connectivity`, and `reduce_setup` for readability.
The root reducer remains responsible for cross-domain invariants, such as suppressing idle shutdown during setup or preventing a stale Wi-Fi result from completing a newer operation.

Effects such as playback commands, Wi-Fi helper calls, selected-backend setup, service restart, timer arm/cancel, and system shutdown remain behind adapters.
An effect runner executes them and feeds success or failure back through the same serialized input path.
This avoids mutating state optimistically in one component and later correcting it in another.

The current `PlaybackBackend` remains the immediate command boundary for dispatch, enqueue, stop, skip, and volume operations.
During migration, the contract should become explicitly provider-neutral and separate command execution from observation without introducing a backend framework.
A selected backend's observer translates the actual player, receiver, or process lifecycle into typed, backend-neutral observations.
Command results may contribute inputs such as `PLAY_COMMAND_ACCEPTED` or `PAUSE_COMMAND_ACCEPTED`, but command success alone cannot manufacture later lifecycle transitions.

The Spotify Web API controller is not itself proof of the local `spotifyd` lifecycle.
EPIC 5 must select and validate a local receiver-observation mechanism on the Raspberry Pi.
A `spotifyd` observer must translate receiver start, item change, pause, natural completion, and loss of observation into the common inputs.
A local-media adapter must be able to emit the same lifecycle inputs when its player process starts, pauses, exits, or fails.
The stub backend must emit deterministic lifecycle inputs directly in tests.

### Projections

- `status.json` exposes the composite snapshot and active issues without causing state changes or adapter calls.
- feedback and LEDs derive one user-facing display state using an explicit priority policy.
- structured logs record inputs, accepted transitions, rejected stale inputs, and effect outcomes without becoming a state store.
- readiness is derived from the snapshot instead of replacing the snapshot with the highest-priority dependency failure.
- queue routing reads the authoritative playback region rather than a backend-owned boolean cache.

## Idle-Shutdown Policy

- Entering confirmed playback `idle` while the appliance is running in normal mode arms one idle timer for that state generation.
- Leaving `idle` cancels or invalidates the timer.
- Entering Wi-Fi setup, playback-backend setup, shutdown, or another explicitly blocking operation cancels or suppresses the timer even if playback is idle.
- When the timer fires, it verifies locally that the authority is still in the same idle generation before requesting shutdown.
- The timer-expiry path must not call the selected playback backend, its observer, or any provider API.
- Playback `unknown`, `starting`, `playing`, or `paused`, and unavailable playback observation, must not be treated as confirmed idle.
- Natural completion of the last direct item, queue item, album, or playlist must eventually produce the same confirmed-idle transition.

Confirmed idle is necessary but not by itself sufficient to arm shutdown; the root appliance policy evaluates the other state regions as well.
The exact list of blocking modes and issues is a requirements decision.
This keeps time measurement in the idle effect while keeping playback and appliance truth in the central authority.

## Interim EPIC 4 Bridge

Until a backend-neutral observer exists, `IdleMonitor` may perform one explicit live activity validation only after a complete idle interval has elapsed.
If playback is active or activity is unknown, it re-arms for another complete interval.
If playback is confirmed inactive, it requests shutdown.
It must not poll Spotify on ordinary timer ticks.

This bridge is intentionally temporary and is marked with a `TODO(EPIC-5)` in code.

## Relationship to EPIC 4

This is an architectural correction to the EPIC 4 passive-activity-cache design, not another cache layered on top of it.
EPIC 4 documents and tests the narrow deadline-scoped bridge needed for current operation.
EPIC 5 must revise the runtime-state portion of that design around the central appliance authority and remove the bridge rather than treating `_cached_player_active` as permanent infrastructure.

## Current Code Smells and Intended Disposition

| Current smell | Consequence | EPIC 5 direction |
|---|---|---|
| Backend `_cached_player_active`, idle `_last_activity`, health cache, and feedback snapshot all imply current state | Consumers can disagree and natural completion has no producer | One `ApplianceState` snapshot; adapter caches cease to be policy authorities |
| Free-form string `ControllerEvent.code` drives runtime decisions | Invalid or incomplete transitions are easy to express and hard to exhaustively test | Typed internal inputs; retain presentation events only as derived compatibility output if needed |
| `FeedbackStateTracker` uses the last event as the display truth | A scan or success event can visually overwrite an active setup or degraded condition | Derive feedback from the full snapshot with an explicit priority policy |
| `RuntimeHealthMonitor` selects one failure using `_STATUS_PRIORITY` | Simultaneous conditions disappear from the authoritative view | Preserve all dependency states and issues; derive one summary only for display |
| `SetupModeManager.status()` reads persisted flags and calls a helper | A status query is not a pure read of runtime truth | Observers publish Wi-Fi facts; status becomes a projection |
| `OperatorStateStore` mixes preferences with setup/auth workflow flags | Durable configuration, user intent, and transient progress have unclear ownership | Separate operator configuration from the minimum durable workflow checkpoints |
| Action and HTTP handlers execute helpers and then mutate flags | Side-effect success and state mutation are split across call sites | Reducer requests effects; effect outcomes return as typed inputs |
| Receiver-auth reconciliation is implemented as nested closures in `build_runtime()` | Workflow rules are difficult to inspect, reuse, and test as a whole | Move auth transitions into the reducer and auth execution into an adapter |
| `SpotifyPlaybackBackend` sounds like a local receiver adapter | The Web API controller and `spotifyd` lifecycle responsibilities are easy to conflate | Rename or split the boundary when migrated, for example Web API command adapter versus receiver observer |
| `PlaybackRequest` and parsed media types are Spotify-URI-specific | Reusing the current command contract for local media or another provider would leak Spotify identifiers into core policy | Introduce only the smallest provider-neutral item reference needed by the local contract test; keep provider metadata in adapters |
| The playback protocol presents enqueue, skip, and volume as universally meaningful | A future backend may not support every operation | Return one normalized unsupported outcome initially; add capabilities only where pre-command policy genuinely needs them |
| Several background threads call independent event sinks | Ordering and stale-result handling are implicit | One serialized input path plus operation/generation identifiers |
| Idle timeout performs an interim live API validation | Policy depends on a backend query and cannot naturally generalize to local media | Arm/cancel from authoritative transitions; validate only the local generation on expiry |

This table is a migration guide, not a mandate to replace every named class.
If an existing class becomes a thin adapter or projection with a clear boundary, keeping it may be simpler than renaming or deleting it.

## Complexity Budget and Simplification Review

The architecture should be reviewed against the smallest implementation that enforces the required invariants.

### Essential for the Playback Fix

- one immutable appliance snapshot, initially with only the fields needed by the first slice
- one serialized state-update path
- typed playback and timer inputs
- one pure transition function with generation-based stale-event rejection
- a backend-neutral playback observer contract
- normalized selected-backend readiness and setup outcomes, including not-required and unsupported cases
- explicit timer arm/cancel and shutdown effects
- read-only projections for migrated consumers

### Reasonable Standard-Library Implementation

- frozen dataclasses plus enums or `Literal` values
- small reducer functions rather than state-machine classes for every region
- one lock-protected store or `queue.Queue`, selected after reviewing callback and thread behavior
- tuples or a small mapping for active issues rather than an error-management framework
- explicit effect dataclasses and a direct dispatcher rather than a general workflow engine
- focused transition tables in tests rather than an event-sourcing or replay system

### Defer Unless a Later Increment Proves the Need

- a third-party state-machine or statechart dependency
- event sourcing, durable event logs, or replay of volatile runtime history
- persistence of playback activity across restart
- a generic workflow language for setup and maintenance operations
- dynamic backend plugins
- real integration with another streaming provider
- runtime backend selection, automatic fallback, simultaneous backends, or cross-backend queue transfer
- local media indexing, library management, metadata extraction, or operator configuration
- distributed coordination beyond this single appliance process
- a complete local-media product implementation; only a deterministic test adapter is needed to prove the observer contract
- a richer operator UI beyond projecting the authoritative state through existing surfaces

### Scope Review Gates

- After the `spotifyd` observation and auth-lifecycle spike, confirm that the proposed state regions match facts the appliance can actually observe.
- At each design review, reject Spotify-specific names or assumptions in core state unless they are explicitly presentation-only diagnostics.
- After the playback vertical slice, review whether the root reducer and effect mechanism are small and legible before migrating setup and health.
- Before each later increment, remove fields, inputs, effects, or abstractions that have no demonstrated consumer or invariant.
- Stop the EPIC after any review gate if the remaining migrations do not justify their complexity; document retained compatibility boundaries explicitly.

## Incremental Delivery Plan

### Increment 0: Receiver Evidence and Scope

- Document the controller Web API, receiver credential, and systemd service boundaries with Pi evidence.
- Validate the deployed `spotifyd` authentication sequence, credential path and permissions, and whether successful authentication requires a service restart.
- Evaluate lightweight local observation options, including whether the deployed build can expose local MPRIS state; the current baseline has `use_mpris = false` and may require build and D-Bus changes.
- Record which start, pause, item-change, natural-end, observer-loss, and service-failure signals are actually reliable.
- Record the minimum normalized readiness, setup, command-result, and observation contract shared by the Spotify path and a no-auth process-backed test backend.
- Select no state-machine abstraction until this evidence is available.

Deliverable: a short evidence note and a go/no-go decision for the smallest reliable receiver observer.

### Increment 1: Appliance-State Foundation in Shadow Mode

- Add the minimal immutable `ApplianceState`, typed inputs, transition result, and serialized store.
- Model appliance lifecycle, operating mode, selected-backend readiness/setup, and the playback region only; add other fields when their migration begins.
- Add pure transition and stale-generation tests.
- Feed existing command outcomes into the new store while retaining current behavior and output surfaces.
- Compare the shadow snapshot with existing status and events during local and Pi validation.

Deliverable: no intended user-visible behavior change and no removal of EPIC 4 safeguards.

### Increment 2: Playback and Idle Vertical Slice

- Add the backend-neutral playback observer contract and selected `spotifyd` observer.
- Feed command outcomes and observed lifecycle facts into the playback reducer.
- Move idle arm, cancel, and expiry validation to appliance-state transitions.
- Move queue routing to authoritative playback state where the evidence is sufficient.
- Add deterministic stub observations and a minimal process-backed test adapter representing local media completion.
- Prove that the no-auth adapter reaches ready through the same backend preparation contract without entering backend-setup mode.
- Remove the expired-deadline Spotify API bridge and `_cached_player_active` from policy decisions.

Deliverable: direct, queue, album, playlist, and simulated local playback all reach the same confirmed-idle shutdown policy without another scan or a timer-time backend call.

### Increment 3: Status, Health, Feedback, and Issues

- Project `status.json`, readiness, feedback, LEDs, and structured logs from `ApplianceState`.
- Preserve simultaneous dependency issues while retaining one explicit display-priority policy.
- Convert health sources into fact publishers rather than owners of a competing aggregate status.
- Retire last-event-wins feedback state and priority-collapsed health as authorities.

Deliverable: policy and every operator-facing surface report the same state generation and active issues.

### Increment 4: Setup, Wi-Fi, Backend Setup, and Service Operations

- Separate persisted operator preferences from durable workflow checkpoints.
- Move setup, Wi-Fi reset, selected-backend setup, and their stale-result handling into typed transitions and effects.
- Keep the current Spotify receiver OAuth browser flow behind its adapter while the reducer handles normalized backend-setup states.
- Represent systemd receiver lifecycle as observed dependency state.
- Add controlled receiver restart as a Spotify backend-setup effect only if Increment 0 proved it necessary.
- Ensure Wi-Fi and playback-backend setup modes suppress idle shutdown through root invariants rather than an `IdleMonitor` flag.

Deliverable: setup and maintenance workflows survive relevant failures or reboots without status queries mutating state.

### Increment 5: Cleanup and Optional Generalization

- Remove compatibility events, caches, flags, and monitors only after no consumer depends on them.
- Rename the Spotify Web API adapter if needed to make its command-only responsibility obvious.
- Confirm that a second streaming adapter or real local-media backend could implement the selected contracts without changing `ApplianceState` or idle policy.
- Decide whether either should become a supported product backend in a separate scoped requirement.
- Update EPIC 4 documentation to identify the superseded architecture and preserve operational history.

Deliverable: one runtime state authority with no duplicate policy state, while retaining only abstractions justified by the completed increments.

## Draft Acceptance Criteria

- Runtime state changes pass through one serialized appliance-state transition path.
- Playback, setup, connectivity, dependency, operation, and issue facts can coexist without a flat combinatorial enum.
- Core appliance state, idle policy, and lifecycle transitions contain no Spotify-specific types or branches.
- A streaming backend requiring setup and a local no-auth backend produce the same normalized readiness and playback lifecycle states.
- Unsupported backend commands fail through a normalized result without requiring a separate state model.
- Recoverable errors do not erase unrelated state, and a user-facing summary is derived by explicit policy.
- Natural playback completion transitions the authoritative state to confirmed idle without another card scan.
- Playback start invalidates an armed idle timer; confirmed idle arms it.
- Direct play, the final queued track, album or playlist completion, and local media use the same idle-shutdown policy.
- A stale timer callback cannot shut down after playback has restarted.
- Observer loss or backend degradation cannot be mistaken for confirmed idle.
- Timer expiry uses only the authoritative snapshot and idle generation; it performs no selected-backend, observer, or provider API call.
- Wi-Fi setup, playback-backend setup, or shutdown mode prevents idle shutdown through a root invariant.
- A stale Wi-Fi, auth, service, or playback result cannot complete a newer operation.
- Health, feedback, and operator status expose projections of the same authoritative snapshot used by control policy.
- Status reads do not mutate runtime state or call operational helpers.
- For the selected Spotify adapter, controller OAuth state, receiver credential state, and receiver service state remain distinct and diagnosable projections of normalized backend facts.
- Normal observation does not depend on periodic provider API calls.
- The implementation remains lightweight enough for Raspberry Pi 3 and testable on a non-Pi development machine.

## Open Decisions

- Which local `spotifyd` signal provides reliable start, pause, item-change, and end observations on the deployed Pi image?
- Does the deployed `spotifyd authenticate` flow require stopping or restarting `spotifyd.service`, and which helper should own that controlled effect?
- Can local MPRIS observation be enabled safely for the system-wide headless service and Pi 3 build, or is another local signal smaller and more reliable?
- What is the smallest preparation/readiness contract that handles Spotify receiver auth and a no-auth local backend without a provider-specific core state or generic auth framework?
- Which playback operations need explicit capabilities because policy must decide before dispatch, and which can simply return unsupported?
- What is the smallest provider-neutral media reference needed for the contract test without prematurely normalizing provider metadata?
- Should the serialized store use a synchronous lock-protected dispatcher or a dedicated input queue?
- Which appliance fields are necessary in Increment 1, and which should be added only with later migrations?
- Should `paused` eventually arm shutdown, and if so, under what explicitly specified policy?
- Which setup, operation, dependency, or issue states block an otherwise eligible idle timer?
- How long should resolved issues remain in the snapshot for diagnostics, if at all?
- Which workflow checkpoints genuinely need persistence across reboot?
- Is Increment 2 enough to close the operational problem, or do the existing setup and health smells justify including Increments 3 and 4 in EPIC 5?

## Reference Inputs

- [Spotifyd authentication documentation](https://docs.spotifyd.rs/configuration/auth.html) for receiver OAuth and `<cache_path>/oauth/credentials.json`
- [Spotifyd configuration documentation](https://docs.spotifyd.rs/configuration/) for config discovery, cache ownership, and MPRIS configuration
- [Spotifyd systemd documentation](https://docs.spotifyd.rs/advanced/systemd.html) for user-versus-system service constraints
- [scripts/runtime/jukebox-spotifyd-auth-helper.sh](/Users/markus/Workspace/jukebox/scripts/runtime/jukebox-spotifyd-auth-helper.sh) for the current receiver-auth helper boundary
- [docs/pi-setup.md](/Users/markus/Workspace/jukebox/docs/pi-setup.md) for the deployed receiver config, cache path, system service, and browser approval flow
- [src/jukebox/adapters/playback_spotify.py](/Users/markus/Workspace/jukebox/src/jukebox/adapters/playback_spotify.py) for the controller-side Web API boundary
