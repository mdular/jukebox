# EPIC 4 Requirements Specification

## Title

EPIC 4: Polish and V2-Oriented Enhancements

## Purpose

This document defines the requirements for EPIC 4 from [spec/roadmap.md](/Users/markus/Workspace/jukebox/spec/roadmap.md).
The goal is to close the loop on the stable V1 appliance baseline from EPIC 3 without reopening the core child-first interaction or weakening the low-maintenance behavior already established on Raspberry Pi 3.

This is a requirements document, not a technical design.
It defines the user-facing polish, selected control and setup expansion, appliance-grade standalone maintenance behavior, and explicit V2 boundary EPIC 4 must deliver.

This document treats the current EPIC 3 baseline recorded in [docs/pi-setup-log.md](/Users/markus/Workspace/jukebox/docs/pi-setup-log.md) and [docs/pi-validation.md](/Users/markus/Workspace/jukebox/docs/pi-validation.md) as the starting point for EPIC 4:

- autonomous reboot, power-cycle, and same-LAN recovery are already expected on the supported Pi baseline
- the scan-to-playback loop is already validated with real cards and external-speaker playback
- the existing runtime state model already distinguishes ready, degraded, and major failure states
- the V1 audio baseline is still external playback through the Pi's USB sound card and powered speaker

## Objective

Refine the stable appliance baseline into a V1 release-worthy standalone jukebox with clearer feedback, selected card-driven controls, lower-friction operator maintenance flows, and a disciplined bridge to V2 that leaves internal speakers and broader field-driven experimentation for the next phase.

## Success Definition

EPIC 4 is complete when the polished appliance baseline demonstrates the following:

- User-facing feedback communicates actual readiness and major scan outcomes clearly enough that the device feels more responsive without appearing falsely ready.
- The selected card-driven control baseline, including the checked D-10 items promoted into scope, works without making ordinary music-card use confusing or fragile.
- Routine operator tasks such as initial Wi-Fi setup, automatic fallback setup access, receiver auth or re-auth, shutdown, and selected recovery flows are supported by a documented companion setup path rather than machine-specific bring-up hacks.
- Automatic Wi-Fi fallback and long-idle shutdown make the appliance more self-managing without weakening the EPIC 3 reboot, recovery, and scan-to-playback baseline.
- The external-speaker and speaker-managed-volume baseline remain explicit for V1, even if optional software-side volume preset cards are added.
- The repository clearly separates EPIC 4 V1 deliverables from the remaining post-roadmap backlog, and it records a post-standalone review checkpoint for further UX experimentation before V2 hardware or interaction commitments are made.

## Decision Checklist

Use this section to review and confirm the open product decisions for EPIC 4. Each decision includes the recommended default so the spec can be approved quickly without losing alternatives.

### D-1 Feedback Translation Scope

EPIC 3 defined the software state model, but EPIC 4 needs to decide how much of that model becomes real user-facing feedback behavior now.

- [ ] Keep EPIC 4 feedback improvements limited to logs and operator diagnostics.
- [x] Promote the existing readiness and scan-state model into a clear user-facing feedback contract, with the ready signal aligned to actual autonomous playback readiness. (Recommended)
- [ ] Expand EPIC 4 into a broader multimodal feedback redesign.

### D-2 Perceived Responsiveness Policy

The concept depends on immediate physical interaction, so EPIC 4 needs a clear rule for when feedback should acknowledge a scan versus when it should confirm playback success.

- [ ] Show only final playback outcomes and do not add separate scan acknowledgement.
- [x] Provide immediate acknowledgement when a scan is received or accepted, while keeping playback success and failure as later distinct outcomes. (Recommended)
- [ ] Favor optimistic acknowledgement even when downstream playback readiness is still uncertain.

Note: the current scanner already provides immediate scan-receipt feedback. The mounted scanner is a Netum NT-91, and its beep behavior can be adjusted with vendor configuration barcodes; see [docs/pi-build.md](/Users/markus/Workspace/jukebox/docs/pi-build.md). EPIC 4 should treat that beep as existing acknowledgement rather than assuming the child receives no feedback before playback confirmation arrives.

### D-3 Stop Action Surface

The roadmap allows an optional stop action, but EPIC 4 should decide whether that belongs in the physical control surface or in card-based interaction.

- [ ] Do not add a stop action in EPIC 4.
- [ ] Add one simple dedicated physical stop control, such as a stop button, and keep stop behavior separate from music-card payloads. (Recommended)
- [x] Add stop behavior through cards, setup cards, or multiple control paths.

Note: start with card-based stop behavior so real usage can be observed before committing to hardware controls. A later phase may still add a physical stop control if the card-based approach proves insufficient after testing.

### D-4 Additional Control Scope

The concept's V2 direction mentions richer controls, but EPIC 4 should decide how much control-surface growth belongs in this roadmap phase.

- [ ] EPIC 4 should include only the selected stop control baseline and defer richer controls. (Recommended)
- [ ] EPIC 4 should add stop plus next-track behavior.
- [x] EPIC 4 should reopen broader control-surface design.

Note: EPIC 4 should still use card-based interaction before committing to many physical controls. The selected EPIC 4 baseline now includes next-track, queue-vs-replacement toggle cards, volume preset cards, and a graceful shutdown card in addition to stop behavior.

### D-5 Volume Control Direction

EPIC 4 needs to define the direction for on-device volume handling without accidentally turning direction-setting into an overgrown controls project.

- [x] Keep volume entirely external for now and defer the built-in direction. The V1 audio setup uses an external speaker and already has practical volume controls, so this is not a current user-experience gap. Revisit built-in volume in the V2 backlog.
- [ ] Define the product baseline for a future integrated volume control centered on the concept's single volume knob, without requiring a broader on-device control surface. (Recommended)
- [ ] Expand EPIC 4 into broader on-device audio-control behavior.

Note: selected EPIC 4 volume preset cards are compatible with this decision because they are optional software-side presets on top of the external-speaker baseline, not a commitment to built-in physical volume hardware.

### D-6 Audio Transition Scope

The stable V1 audio baseline is still the external speaker path, but EPIC 4 needs to decide whether it only defines the bridge to V2 audio or also starts the transition.

- [x] Keep EPIC 4 entirely on the external-speaker baseline with no explicit V2 audio bridge.
- [ ] Preserve the validated external-speaker baseline while defining the direction, constraints, and acceptance boundary for a later internal-audio transition. (Recommended)
- [ ] Require EPIC 4 to complete an integrated internal-audio transition.

### D-7 Standalone Receiver Auth Flow

The roadmap calls for an appliance-grade standalone receiver-auth or re-auth path, so EPIC 4 needs to decide how self-contained that maintenance flow must be.

- [ ] Keep receiver auth and re-auth as expert-only manual bring-up steps.
- [ ] Require one documented standalone operator flow for receiver auth or re-auth, such as a browser-based flow from another device, without relying on harvested tokens or machine-specific hacks. (Recommended)
- [x] Expand EPIC 4 into a broader companion configuration interface.

Note: the selected direction is a browser-based companion flow that can cover initial Wi-Fi setup, receiver auth or re-auth, and selected recovery actions. For a device with no Wi-Fi configured, the current expectation is an AP or captive-portal style setup path. One expected recovery path is a Wi-Fi reset card so the device can re-enter setup without shell access.

### D-8 Maintenance Ergonomics Scope

EPIC 4 should improve maintenance only where it reduces real operator friction. This decision defines how far that work goes.

- [ ] Documentation cleanup only.
- [x] Add focused maintenance ergonomics, such as clearer operator guidance and narrowly scoped helper flows, without turning EPIC 4 into a general management UI. (Recommended)
- [ ] Build a broader dashboard or management surface.

Note: a lightweight healthcheck endpoint returning diagnostic JSON and current config state, including card-driven toggles, fits the selected maintenance ergonomics scope as long as it stays operator-facing and does not turn into a full dashboard.

### D-9 Reliability Regression Gate

Polish work only counts if it preserves the appliance baseline from EPIC 3, so EPIC 4 needs a clear validation threshold.

- [ ] Validate only the new polish features
- [x] Revalidate the EPIC 3 boot, recovery, and scan-to-playback baseline after EPIC 4 changes, alongside the new polish behavior. (Recommended)
- [ ] Require extended unattended soak testing as an EPIC 4 completion condition.

Note: rerun the network-flakiness validation when EPIC 4 changes touch networking or network-dependent playback behavior. Because the selected EPIC 4 scope now includes automatic Wi-Fi fallback and companion setup networking, that network-interruption validation is part of the EPIC 4 regression gate.

### D-10 V1 Scope Boundary

The roadmap's parking-lot items now need a deliberate V1 release boundary: some of the reviewed ideas belong in EPIC 4, while the rest should stay in the post-roadmap backlog.

- [ ] Fold post-roadmap ideas into EPIC 4 whenever time permits.
- [x] Promote the checked candidate items below into EPIC 4 scope for the V1 release and keep the unchecked remainder as the labeled post-roadmap backlog. (Recommended)
- [ ] Treat EPIC 4 as the place to broadly reopen deferred feature work.

Note: the checked items below count as EPIC 4 deliverables. The unchecked items remain backlog and should be revisited after the device has seen polished standalone household use so later UX experimentation and V2 planning are grounded in field observations rather than speculation.

#### Scope and Backlog Review

Use this checklist to distinguish which deferred ideas are now promoted into EPIC 4 scope and which remain post-roadmap backlog.

##### Card and control experiments

- [x] Additional setup cards beyond the selected EPIC 4 stop and reset flows
- [x] Next-track cards
- [x] Queue-vs-replacement toggle cards
- [x] Volume preset cards
- [x] Shutdown card (graceful)
- [ ] Other experimental card-driven control modes beyond the selected EPIC 4 baseline
- [ ] Later physical controls if card-driven controls prove insufficient

##### Setup and operator tooling beyond the selected EPIC 4 baseline

- [x] Automatic Wi-Fi fallback network
- [ ] Broader management UI beyond the selected setup, auth, and healthcheck flows
- [ ] Expanded diagnostic or config API surface beyond the selected lightweight maintenance endpoint

##### Content and playback expansion

- [ ] Printer-friendly QR card sheet generator with metadata, artwork, and Spotify-link-to-URI conversion
- [ ] Local playback fallback and media mapping
- [ ] Queue mode as a primary playback model
- [ ] Story cards, podcast cards, and other non-music card types

##### Appliance platform and hardware evolution

- [ ] Read-only filesystem mode
- [ ] OTA updates
- [x] Auto-shutdown after a long idle period
- [ ] Built-in volume control
- [ ] Internal speaker selection, amplifier integration, and enclosure acoustics

## In Scope

- Translating the existing appliance state model into clearer user-facing feedback behavior that complements the scanner's built-in scan beep.
- Refining readiness and scan feedback so the device feels more responsive without overstating readiness.
- A selected card-driven control baseline that includes stop, next-track, queue-vs-replacement toggles, volume preset cards, graceful shutdown, Wi-Fi reset, and selected setup-entry cards that remain explicit operator or control actions rather than ordinary music cards.
- A browser-based companion setup, auth, and recovery interface from another device, including no-Wi-Fi bring-up and selected reset or re-auth flows.
- Automatic Wi-Fi fallback behavior that helps the appliance re-enter a documented setup path when Wi-Fi is absent or setup mode is explicitly requested.
- Lightweight maintenance ergonomics such as a healthcheck endpoint returning diagnostic JSON and current config state.
- Long-idle auto-shutdown behavior that preserves simple recovery through normal power-on.
- Preserving the external speaker-managed volume baseline while explicitly deferring built-in volume and internal-audio work to backlog.
- Regression validation needed to prove the polished experience still meets the EPIC 3 reliability baseline after the selected EPIC 4 networking, control, setup, and shutdown changes.
- A labeled post-roadmap backlog plus a post-standalone review checkpoint that separates deferred expansion ideas from EPIC 4 deliverables.

## Out of Scope

- Reopening accepted card payload formats, supported Spotify URI types, duplicate suppression, or the default replacement-oriented scan semantics from earlier EPICs.
- Story cards, podcast cards, local playback fallback, printer-friendly QR generation, or other content-feature expansion beyond the core jukebox loop.
- Queue mode as the new primary playback model beyond the selected card-driven replace-versus-queue toggle behavior.
- OTA updates, read-only filesystem mode, or other appliance-platform work not selected in D-10.
- A child-facing daily-use management UI or a broader dashboard beyond the selected setup, auth, status, and healthcheck flows.
- Built-in volume controls, internal speakers, amplifier integration, enclosure acoustics, or other V2 audio implementation work in EPIC 4.
- Additional physical controls beyond the selected card-first EPIC 4 control baseline.

## Functional Requirements

### FR-1 User-Facing Readiness and Feedback Contract

EPIC 4 shall define a user-facing feedback contract built on the EPIC 3 state model.

Requirements:

- The polished baseline shall define what the user-facing feedback shows for booting, degraded or waiting, ready, scan acknowledgement, duplicate suppression, invalid payload, unsupported content, playback success, playback failure, supported control actions, and supported setup actions.
- The ready feedback shall remain reserved for a state where autonomous scan-to-playback is actually usable.
- A degraded or dependency-recovery state shall remain distinguishable from a fully ready state.
- The feedback contract shall account for the scanner's existing scan-receipt beep so device-level acknowledgement and software-level readiness or playback feedback do not conflict.
- The feedback contract shall remain understandable without requiring the operator to read logs during normal use.

Related decisions: `D-1 Feedback Translation Scope`, `D-2 Perceived Responsiveness Policy`, and `D-9 Reliability Regression Gate`.

### FR-2 Perceived Responsiveness

EPIC 4 shall improve the sense of responsiveness without making the device misleading about what has actually happened.

Requirements:

- The selected feedback baseline shall define which part of immediate acknowledgement comes from scanner hardware, software feedback, or both.
- A valid scan shall produce immediate observable acknowledgement, but playback success or failure shall remain a later distinct outcome.
- Duplicate suppression, invalid payloads, unsupported content, and unsupported control actions shall remain distinguishable from successful playback.
- The responsiveness model shall not depend on claiming readiness or success before the underlying state is actually reached.

Related decisions: `D-1 Feedback Translation Scope` and `D-2 Perceived Responsiveness Policy`.

### FR-3 Card-Based Control and Setup Baseline

If EPIC 4 includes control or setup cards, they shall remain explicit and clearly separated from the ordinary music-card interaction model.

Requirements:

- The selected EPIC 4 control baseline shall document each supported control or setup card and the outcome it triggers.
- The supported baseline shall include stop, next-track, queue-vs-replacement toggle cards, volume preset cards, a graceful shutdown card, Wi-Fi reset, and at least one additional setup-entry card tied to the companion maintenance flow.
- Control or setup cards shall be distinguishable from ordinary music cards in both documentation and runtime feedback.
- Repeated use of a supported control action while its target state is already true or unavailable shall fail safely rather than destabilize the runtime.
- Operator-facing cards shall be documented as operator-facing and not implied to be ordinary child-play cards.

Related decisions: `D-3 Stop Action Surface`, `D-4 Additional Control Scope`, `D-7 Standalone Receiver Auth Flow`, and `D-10 V1 Scope Boundary`.

### FR-4 Control-Surface and Playback-Mode Discipline

EPIC 4 shall keep the added control behavior within a narrow child-first scope.

Requirements:

- Added controls shall not change the core rule that music cards remain the primary interaction path.
- The selected replace-versus-queue behavior shall be explicitly documented, including any content-type limits needed to keep the behavior honest.
- Added controls shall not silently alter the baseline behavior for households that never use control cards.
- Maintenance or setup behavior shall remain separate from the ordinary child-facing music-card baseline even when delivered through cards.

Related decisions: `D-3 Stop Action Surface`, `D-4 Additional Control Scope`, and `D-10 V1 Scope Boundary`.

### FR-5 External Volume Baseline and Optional Preset Cards

EPIC 4 shall preserve the current external-volume baseline while allowing the selected preset-card experiments.

Requirements:

- The current external speaker shall remain the only required physical volume-control surface for EPIC 4.
- If volume preset cards are selected, they shall be documented as optional software-side conveniences rather than a redefinition of the hardware volume direction.
- The deliverables shall state explicitly that built-in volume control and internal audio remain deferred.
- EPIC 4 shall not imply partial support for built-in volume or internal audio if those features are not actually delivered.

Related decisions: `D-5 Volume Control Direction`, `D-6 Audio Transition Scope`, and `D-10 V1 Scope Boundary`.

### FR-6 Companion Setup, Auth, Recovery, and Automatic Wi-Fi Fallback

EPIC 4 shall define a self-contained operator path for setup, receiver auth or re-auth, selected recovery actions, and automatic re-entry into setup access when Wi-Fi is absent.

Requirements:

- The supported operator flow shall cover receiver auth or re-auth and initial setup on a device that does not yet have Wi-Fi configured.
- The selected setup flow may use an AP, captive-portal, or equivalent browser-based path from another device, but it shall be documented as one supported baseline.
- Selected recovery actions, such as returning the device to Wi-Fi setup or requesting receiver re-auth, shall not require source edits or shell-only recovery steps.
- The selected automatic fallback behavior shall define when the appliance re-enters the documented Wi-Fi setup path and when it stays in ordinary degraded recovery instead.
- The workflow shall remain separate from the normal child-facing interaction model.
- The documentation shall distinguish receiver-side auth or session bootstrap from the controller app's own secret provisioning requirements.
- Secrets and credentials shall remain outside the repository and outside committed files.

Related decisions: `D-7 Standalone Receiver Auth Flow`, `D-8 Maintenance Ergonomics Scope`, and `D-10 V1 Scope Boundary`.

### FR-7 Maintenance Ergonomics

EPIC 4 shall reduce operator friction where that improves maintainability without broadening the product into a management console.

Requirements:

- The repository shall document the operator flows needed for routine validation, setup, receiver auth or re-auth, recovery, selected EPIC 4 control cards, automatic Wi-Fi fallback expectations, and shutdown behavior.
- If EPIC 4 includes a healthcheck or diagnostic endpoint, the documentation shall define what state and config information it exposes and how operators are expected to use it.
- Maintenance guidance shall be understandable without source-level knowledge.
- The selected maintenance ergonomics shall remain narrowly scoped to real appliance upkeep tasks.
- Any helper flow introduced for maintenance shall preserve the headless Pi direction and avoid requiring a desktop session on the Pi itself.

Related decisions: `D-7 Standalone Receiver Auth Flow` and `D-8 Maintenance Ergonomics Scope`.

### FR-8 Shutdown and Idle-Power Behavior

EPIC 4 shall define how graceful shutdown and long-idle auto-shutdown fit the appliance behavior.

Requirements:

- The supported shutdown card shall trigger a documented graceful shutdown path rather than an abrupt power loss assumption.
- Long-idle auto-shutdown shall remain conservative and shall not interrupt active playback or a clearly recent scan or control interaction.
- The deliverables shall define the expected recovery path after either shutdown mechanism, and that path shall remain simple enough for family use.
- Shutdown behavior shall remain observable through feedback and operator diagnostics.

Related decisions: `D-4 Additional Control Scope`, `D-8 Maintenance Ergonomics Scope`, and `D-10 V1 Scope Boundary`.

### FR-9 Reliability Preservation

EPIC 4 shall preserve the hardened appliance behavior already established in EPIC 3.

Requirements:

- The polished baseline shall continue to boot into a usable autonomous scan-to-playback path without new routine manual recovery steps.
- Feedback polish shall not present the device as ready before the underlying playback path is actually ready.
- Added control, setup, networking, or shutdown behavior shall not weaken the supported reboot, power-cycle, or same-LAN recovery expectations established in EPIC 3.
- Regression validation shall cover both the new EPIC 4 behavior and the carried-forward EPIC 3 boot, recovery, and scan-to-playback baseline.
- Because EPIC 4 now includes networking changes, full network-interruption reruns are required as part of EPIC 4 validation.

Related decisions: `D-1 Feedback Translation Scope`, `D-7 Standalone Receiver Auth Flow`, `D-9 Reliability Regression Gate`, and `D-10 V1 Scope Boundary`.

### FR-10 Core Interaction Continuity

EPIC 4 shall refine the appliance without reopening the already validated core jukebox behavior.

Requirements:

- Music cards shall continue to use the accepted Spotify URI behavior established in earlier EPICs unless an explicit EPIC 4 exception is documented.
- If control or setup cards are introduced, their semantics shall be explicitly documented and distinguishable from ordinary music cards.
- Duplicate suppression and the default playback replacement semantics shall remain consistent with the prior baseline unless an explicit EPIC 4 exception is documented.
- The project shall not rely on fake QR payloads, fake credentials, or placeholder business content to represent supported control or setup behavior.
- Any new operator or control workflow shall be clearly separated from the ordinary music-card path.

Related decisions: `D-3 Stop Action Surface`, `D-4 Additional Control Scope`, and `D-10 V1 Scope Boundary`.

### FR-11 V1 Boundary and Post-Standalone Review Checkpoint

EPIC 4 shall leave a disciplined V1 completion boundary rather than an ambiguous partially supported future roadmap.

Requirements:

- The EPIC 4 deliverables shall identify which reviewed parking-lot ideas were promoted into the V1 release scope and which remain explicitly deferred after the roadmap is complete.
- Deferred items shall be labeled as backlog rather than implied product behavior.
- The outputs shall record a post-standalone review checkpoint for the selected EPIC 4 control and feedback experiments so later V2 control or feedback work can be guided by field usage.
- The documentation shall make clear that V2 remains focused on internal speakers and any later physical feedback, control, or usage-mode decisions informed by real standalone use.

Related decisions: `D-6 Audio Transition Scope` and `D-10 V1 Scope Boundary`.

## Non-Functional Requirements

### NFR-1 Child-First Simplicity

The polished baseline shall remain consistent with the concept's child-first interaction model.

Requirements:

- Added feedback and controls should make the device easier to understand, not more complex.
- Routine child use should still center on placing a music card in the scan bay, even if optional control or setup cards are introduced.
- The selected EPIC 4 additions should avoid introducing menus, hidden modes, or multi-step interaction sequences for ordinary play.

Related decisions: `D-1 Feedback Translation Scope`, `D-3 Stop Action Surface`, and `D-4 Additional Control Scope`.

### NFR-2 Reliability Over Polish

EPIC 4 shall preserve the low-maintenance appliance posture established in EPIC 3.

Requirements:

- A polish improvement should not be accepted if it weakens ordinary boot, recovery, or playback reliability.
- The polished runtime should remain honest about degraded states rather than hiding them behind more attractive feedback.
- Normal operation should not depend on more frequent operator intervention than the hardened EPIC 3 baseline.

Related decisions: `D-1 Feedback Translation Scope`, `D-8 Maintenance Ergonomics Scope`, and `D-9 Reliability Regression Gate`.

### NFR-3 Raspberry Pi 3 and Headless Fit

EPIC 4 shall remain appropriate for the project's Raspberry Pi 3 and headless-runtime constraints.

Requirements:

- The selected EPIC 4 scope should remain lightweight enough for headless Raspberry Pi 3 operation.
- Operator flows may use another device when needed, but they should not require a desktop environment on the Pi.
- The project should remain runnable and testable on non-Pi development machines where practical, even though final polish validation may involve Pi hardware.

Related decisions: `D-6 Audio Transition Scope`, `D-7 Standalone Receiver Auth Flow`, and `D-8 Maintenance Ergonomics Scope`.

### NFR-4 Maintainability and Repository Hygiene

EPIC 4 shall improve maintainability without weakening the project's documentation and secret-handling discipline.

Requirements:

- Maintenance flows should be documented clearly enough to repeat on another Pi of the same class.
- No credentials or secrets shall be committed to the repository.
- Hidden one-off setup state should be treated as a defect in the EPIC 4 deliverable.

Related decisions: `D-7 Standalone Receiver Auth Flow` and `D-8 Maintenance Ergonomics Scope`.

### NFR-5 Scope Discipline

EPIC 4 shall stay reviewable as a focused V1 closure phase rather than dissolving into open-ended feature expansion.

Requirements:

- The selected EPIC 4 deliverables should remain reviewable as one focused polish and standalone-closure phase.
- Deferred post-roadmap ideas should stay explicitly deferred unless a new spec adopts them.
- The documentation should make it easy to tell what is supported now, what is selected for later review, and what is only a future possibility.

Related decisions: `D-6 Audio Transition Scope`, `D-8 Maintenance Ergonomics Scope`, and `D-10 V1 Scope Boundary`.

## Acceptance Criteria

### AC-1 Honest Ready Feedback

- Given the device is still booting or waiting on a dependency needed for autonomous playback
- When the user-facing feedback is observed
- Then it does not present the same ready indication as a fully usable runtime
- And the waiting or degraded condition remains distinguishable from ready

### AC-2 Immediate Scan Acknowledgement

- Given the device is in a ready state
- When a valid card is scanned
- Then the selected EPIC 4 feedback baseline provides clear immediate acknowledgement through the scanner beep, software feedback, or both
- And later playback success or failure remains distinguishable from that acknowledgement

### AC-3 Duplicate, Invalid, and Unsupported Outcome Clarity

- Given the device is ready for scans
- When the same card is scanned again within the duplicate window or an invalid, unsupported, or unsupported-control payload is received
- Then the resulting feedback makes those outcomes distinguishable from successful playback or successful control actions
- And the device does not silently ignore the event

### AC-4 Selected Control Card Simplicity

- Given the selected EPIC 4 baseline includes stop, next-track, mode-toggle, volume preset, shutdown, and setup cards
- When one of those supported cards is used under its documented conditions
- Then the resulting action is observable and does not require changing the ordinary music-card payload model
- And repeated use of a no-longer-applicable control fails safely and observably

### AC-5 Queue Toggle Honesty

- Given the selected EPIC 4 baseline includes replace-versus-queue controls
- When the operator reviews or uses the documented queue behavior
- Then any content-type limits or fallback behavior are explicit
- And the device does not pretend unsupported queue behavior works for all card types

### AC-6 Companion Setup, Auth, and Automatic Wi-Fi Fallback

- Given a device has no Wi-Fi configured, has entered a supported fallback setup mode, or requires receiver-side auth or re-auth
- When the operator follows the documented EPIC 4 companion flow from the supported environment
- Then Wi-Fi and receiver auth can be completed without harvested tokens, source edits, or machine-specific hacks
- And the required secrets remain outside the repository

### AC-7 Shutdown and Auto-Shutdown

- Given the device is idle long enough or the supported shutdown card is used
- When the shutdown behavior is triggered under its documented conditions
- Then the shutdown path is graceful and observable
- And the documented recovery path remains simple enough for family use

### AC-8 Reliability Regression Preservation

- Given the EPIC 4 changes are in place
- When the documented reboot, recovery, network-interruption, and scan-to-playback validation flow is rerun
- Then the polished system still meets the carried-forward EPIC 3 reliability expectations
- And no new routine daily intervention step has been introduced

### AC-9 Audio Direction Clarity

- Given an operator reviews the EPIC 4 deliverables
- When checking what EPIC 4 does and does not change about the audio path
- Then the continued external-speaker and speaker-managed-volume baseline is explicit
- And the boundary between optional preset-card behavior and deferred built-in audio or volume work is clear

### AC-10 Maintenance Ergonomics

- Given the assembled appliance needs routine validation, setup, auth, recovery, or a supported maintenance task
- When the operator follows the repository guidance and any selected diagnostic surface
- Then the workflow is understandable without source-level knowledge
- And it remains narrowly scoped to practical appliance upkeep rather than a broad daily-use management interface

### AC-11 Core Interaction Continuity

- Given cards and scan scenarios that already passed earlier EPIC validation
- When they are used against the EPIC 4 baseline
- Then supported Spotify URI behavior, duplicate suppression, and default playback replacement remain consistent unless an explicit EPIC 4 exception is documented
- And any supported control or setup cards are explicitly documented rather than implied through placeholder behavior

### AC-12 V1 Boundary and Review Checkpoint

- Given parking-lot ideas still exist after EPIC 4 planning
- When the operator reviews the EPIC 4 outputs
- Then the promoted V1 items and the remaining backlog are labeled explicitly
- And the outputs include a post-standalone review checkpoint for deciding what, if anything, should evolve further in V2

## Deliverables

- A requirements-backed user-facing feedback contract for the polished appliance baseline, including how scanner-beep acknowledgement and software feedback work together.
- A selected EPIC 4 card-driven control baseline that includes stop, next-track, replace-versus-queue toggles, volume preset cards, graceful shutdown, and selected setup-entry or recovery cards while staying compatible with the child-first interaction model.
- A documented companion setup, auth, and recovery path suited to the headless appliance, including automatic Wi-Fi fallback behavior.
- A defined idle-shutdown behavior and recovery expectation appropriate for family appliance use.
- An explicit statement that EPIC 4 keeps the V1 external-speaker and external-volume baseline while deferring built-in audio controls and internal speakers.
- Updated operator guidance, diagnostic-surface expectations, and regression-validation expectations that preserve the EPIC 3 baseline.
- A labeled post-roadmap backlog plus a post-standalone review checkpoint for future control, feedback, and V2 planning.

## Handoff Questions

These are not EPIC 4 blockers, but they should be captured so the next planning cycle starts from an explicit V1 release baseline rather than vague carry-over.

### H-1 Internal Audio Delivery Phase

This determines how the project should treat the concept's internal speaker direction after the roadmap is complete.

- [ ] Start a dedicated post-roadmap phase for integrated internal audio once EPIC 4 polish is stable. (Recommended)
- [ ] Fold internal audio into ongoing EPIC 4 work if possible
- [ ] Decide later

### H-2 Post-Standalone Control and Feedback Review

This determines how the project should evaluate the selected EPIC 4 control and feedback experiments after the standalone appliance has seen real household use.

- [ ] Use field usage to decide whether any EPIC 4 card-driven controls or feedback behaviors should evolve into V2 physical controls or richer indicators. (Recommended)
- [ ] Freeze the EPIC 4 control and feedback baseline as the long-term direction
- [ ] Decide later

### H-3 Card Workflow Tooling

This determines whether printer-friendly QR card generation should be considered as a future workflow improvement once the appliance baseline itself is stable.

- [ ] Consider a dedicated post-roadmap workflow for printer-friendly QR card generation from supported Spotify inputs. (Recommended)
- [ ] Treat card generation as out of scope indefinitely
- [ ] Decide later

### H-4 Appliance Platform Extras

This determines how to treat the remaining roadmap parking-lot items that affect appliance operations more than the core scan-to-playback loop.

- [ ] Keep items such as read-only filesystem mode, OTA updates, and any broader management surface in a separate post-roadmap backlog. (Recommended)
- [ ] Roll those platform ideas into the next immediate implementation phase
- [ ] Decide later

## Notes

- This document intentionally builds on the current EPIC 3 baseline recorded in [docs/pi-setup-log.md](/Users/markus/Workspace/jukebox/docs/pi-setup-log.md) and [docs/pi-validation.md](/Users/markus/Workspace/jukebox/docs/pi-validation.md) rather than reopening those hardening outcomes.
- This document intentionally promotes the checked D-10 items into EPIC 4 scope because they complete the V1 standalone appliance boundary described in [spec/roadmap.md](/Users/markus/Workspace/jukebox/spec/roadmap.md).
- This document intentionally leaves V2 centered on internal speakers and any later physical feedback, control, or usage-mode work that should be informed by real standalone usage.
- This document intentionally does not choose a technical module layout, GPIO wiring plan, browser implementation, or auth implementation mechanism.
- Those choices belong in [spec/EPIC-4-technical.md](/Users/markus/Workspace/jukebox/spec/EPIC-4-technical.md).
