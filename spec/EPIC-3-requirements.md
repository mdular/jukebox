# EPIC 3 Requirements Specification

## Title

EPIC 3: Appliance Hardening and Build Readiness

## Purpose

This document defines the requirements for EPIC 3 from [spec/roadmap.md](/Users/markus/Workspace/jukebox/spec/roadmap.md).
The goal is to turn the working Raspberry Pi 3 prototype into a stable, low-maintenance appliance candidate that is ready for enclosure integration and normal family use.

This is a requirements document, not a technical design.
It defines the hardening outcomes EPIC 3 must deliver and captures the remaining product-level decisions that should be settled before implementation details are specified.

This document treats the recorded EPIC 2 findings in [docs/pi-setup-log.md](/Users/markus/Workspace/jukebox/docs/pi-setup-log.md) as current baseline inputs:

- the `evdev` scanner path is validated on the Pi
- the USB sound card is the V1 audio baseline
- `/etc/asound.conf` is required today for service-level USB audio output
- clean reboot now returns `jukebox.service` to a stable ready state without a restart loop
- the remaining prototype gap is receiver visibility after reboot, which still depends on manual activation from another Spotify client
- the remaining hardening work must solve the receiver-session and Connect-discovery boundary, not only the controller app's Spotify Web API token handling

## Objective

Define the requirements for an autonomous, headless Raspberry Pi 3 jukebox that returns to usable scan-to-playback behavior after reboot, power restoration, and ordinary same-LAN network interruptions without requiring phone-side receiver activation.

## Success Definition

EPIC 3 is complete when the hardened Raspberry Pi 3 baseline demonstrates the following:

- The device returns to a usable scan-to-playback state after reboot or power restoration without manual launch commands or another Spotify client waking the receiver.
- Temporary same-LAN Wi-Fi interruptions and temporary Spotify-side availability issues recover cleanly enough for normal household use.
- Degraded runtime states remain observable and distinguishable instead of failing silently or appearing falsely ready.
- The documented operational path no longer depends on fragile prototype-only steps that would be unreasonable after enclosure assembly.
- Build-readiness checkpoints are explicit enough that enclosure work does not block scanner reliability, power access, cable routing, or serviceability.

## Decision Checklist

Use this section to review and confirm the open product decisions for EPIC 3. Each decision includes the recommended default so the spec can be approved quickly without losing alternatives.

### D-1 Receiver Autonomy Strategy

EPIC 2 proved that the current `raspotify` prototype path still requires manual receiver activation after reboot. EPIC 3 needs an outcome-level decision on whether appliance autonomy is more important than preserving the current receiver package.

- [ ] EPIC 3 must keep `raspotify` as the only supported receiver path.
- [x] EPIC 3 is outcome-driven: it may replace or augment the current receiver path if that is required to remove phone-side activation after reboot. (Recommended)
- [ ] EPIC 3 should support multiple receiver paths in parallel.

### D-2 Startup Readiness Contract

The prototype should not look ready before autonomous playback is actually available, but the requirements still need to define whether a degraded waiting state is acceptable while dependencies recover.

- [ ] Treat the system as ready once the controller service is running, even if playback dependencies are still recovering.
- [x] Expose a degraded but observable waiting state until autonomous scan-to-playback is available, and reserve the ready state for a fully usable system. (Recommended)
- [ ] Delay all operator-facing readiness feedback until every dependency is fully recovered.

### D-3 Supervision Model

EPIC 3 needs a clear recovery expectation for the controller and playback stack, but this requirements document should stay at the behavior level rather than prescribe a specific `systemd` implementation.

- [ ] Best-effort recovery only; persistent runtime failures may require operator intervention.
- [x] Require bounded unattended recovery for transient failures, with a stable service baseline and clear degraded-state feedback. (Recommended)
- [ ] Require aggressive self-healing for all failure classes before EPIC 3 can complete.

### D-4 Network Recovery Scope

The hardening target should improve ordinary household resilience without pulling broader connectivity features into this EPIC.

- [ ] Expand EPIC 3 to include hotspot, captive-portal, or offline fallback flows.
- [x] Limit EPIC 3 network recovery to same-LAN Wi-Fi reconnect and temporary Spotify/API availability issues. (Recommended)
- [ ] Treat network recovery as best effort only and leave recovery expectations mostly undefined.

### D-5 Feedback Scope

EPIC 3 needs appliance-grade feedback semantics, but the roadmap still allows hardware-visible feedback wiring to be handled later as long as the state model is settled now.

- [ ] Keep EPIC 3 observability limited to logs and service diagnostics only.
- [x] Define the required state model for ready, scan, playback success, degraded, and error states so it works in logs now and can map to future hardware indicators later. (Recommended)
- [ ] Require final LED wiring and behavior as an EPIC 3 completion condition.

### D-6 Build-Readiness Checkpoints

The enclosure does not need to be fully designed in EPIC 3, but this EPIC does need to define how specific the physical integration constraints must be before assembly starts.

- [x] Capture only high-level enclosure notes and leave the integration details for later.
- [ ] Define concrete checkpoints for scanner mounting assumptions, cable routing, power access, and service access so enclosure work does not block stable runtime behavior. (Recommended)
- [ ] Fully define enclosure construction details as part of EPIC 3.

### D-7 Maintenance Guidance Depth

Once the device is assembled, recovery and validation should not depend on source-level knowledge. EPIC 3 needs to define the minimum guidance that must exist for routine maintenance and safe troubleshooting.

- [ ] Keep only developer-oriented bring-up notes.
- [x] Provide minimum operator guidance for routine validation, recovery checks, and safe troubleshooting after assembly. (Recommended)
- [ ] Require a full end-user maintenance manual in EPIC 3.

### D-8 Validation Depth

The roadmap calls for appliance hardening, so EPIC 3 needs a stronger validation threshold than EPIC 2 without expanding into long soak testing unless that is explicitly chosen.

- [ ] One successful reboot and one successful power-cycle test are sufficient.
- [x] Require repeated clean reboot validation plus at least one controlled power-cycle and temporary network interruption recovery test. (Recommended)
- [ ] Require extended unattended soak testing before EPIC 3 can complete.

## In Scope

- Autonomous boot-to-playback behavior on Raspberry Pi 3 after reboot and power restoration.
- Recovery expectations for transient receiver, network, and Spotify-side availability issues within the same-LAN home setup.
- A defined service-readiness and degraded-state contract for the controller and playback stack.
- Observable runtime states for normal, degraded, and error flows.
- Build-readiness checkpoints for scanner mounting assumptions, cable routing, power access, and service access.
- Minimum operational guidance needed to validate, recover, and maintain the assembled V1 device.
- Preserving or explicitly replacing the current headless env-file configuration model in a documented way.

## Out of Scope

- Internal speaker integration, amplifier selection, or other V2 audio work.
- New control-surface features such as volume knob, next-track, or expanded interaction modes.
- Local media fallback, queue behavior, story-card behavior, or other playback-mode expansion.
- Hotspot setup flows, captive portal setup, offline playback, OTA updates, or read-only filesystem work.
- Final LED hardware wiring or enclosure construction details beyond the runtime-related checkpoints needed for build readiness.
- Companion apps, broader management tooling, or other configuration UX beyond the current headless maintenance model.

## Functional Requirements

### FR-1 Autonomous Boot and Power-Restore Readiness

The hardened EPIC 3 baseline shall return to a usable autonomous playback state after reboot or power restoration.

Requirements:

- After a clean reboot or power restoration, the system shall return to a state where a valid scan can trigger playback without another Spotify client waking the receiver.
- The system shall not present the same ready state for a partially recovered runtime that still cannot complete autonomous playback.
- If dependencies are still recovering, the system shall remain observable in a not-ready or degraded state rather than failing silently.
- The boot-to-ready contract shall be documented in a way that is actionable for validation and maintenance.

Related decisions: `D-1 Receiver Autonomy Strategy`, `D-2 Startup Readiness Contract`, and `D-8 Validation Depth`.

### FR-2 Receiver Availability Without Manual Activation

EPIC 3 shall eliminate the current post-reboot dependency on manual receiver activation from another Spotify client.

Requirements:

- The supported playback path shall make the on-device receiver available for playback after boot without requiring a phone or desktop Spotify client to wake it.
- Receiver visibility problems shall be treated as a distinct degraded or error condition rather than being hidden behind a generic playback failure.
- The supported playback path shall define separate handling for controller-side Spotify Web API credentials and receiver-side Spotify Connect session persistence.
- Receiver targeting shall not depend on a previously cached Spotify device ID remaining stable across reboot or reconnect.
- The supported receiver path shall remain consistent with the project's headless appliance direction.
- The requirements shall prioritize autonomous playback behavior over preserving the current receiver package.

Related decisions: `D-1 Receiver Autonomy Strategy` and `D-2 Startup Readiness Contract`.

### FR-3 Recovery From Transient Runtime Failures

The EPIC 3 baseline shall recover reasonably from ordinary household interruptions without needing ad hoc service restarts or source-level debugging.

Requirements:

- The system shall define expected behavior for temporary same-LAN Wi-Fi loss and recovery.
- The system shall define expected behavior for temporary Spotify API, Connect discovery, or receiver availability problems.
- Transient failures shall trigger unattended recovery attempts or an observable degraded state rather than silent non-response.
- Recovery expectations outside the selected EPIC 3 scope shall be documented explicitly instead of implied.

Related decisions: `D-3 Supervision Model`, `D-4 Network Recovery Scope`, and `D-8 Validation Depth`.

### FR-4 Service Supervision and Failure Handling

The controller and playback stack shall have a defined failure-handling contract that supports unattended use without hiding persistent faults.

Requirements:

- The runtime shall have a documented expectation for how startup failures, transient failures, and persistent failures are handled.
- Transient failures shall not degrade into ambiguous restart loops or silent process exit.
- Invalid configuration or missing runtime secrets shall remain distinguishable from transient runtime failures.
- Persistent failures shall remain observable enough that an operator can tell the difference between a recovery-in-progress state and a hard fault.

Related decisions: `D-2 Startup Readiness Contract`, `D-3 Supervision Model`, and `D-7 Maintenance Guidance Depth`.

### FR-5 Observable State Model

EPIC 3 shall define the appliance feedback states needed for both software diagnostics now and possible hardware indicators later.

Required observable states:

- Booting or not ready
- Degraded or waiting on dependency recovery
- Ready for scan
- Scan received
- Valid scan accepted
- Duplicate suppressed
- Invalid payload
- Unsupported content type
- Playback started
- Playback failed
- Controller playback API auth unavailable
- Scanner unavailable
- Receiver unavailable
- Network unavailable or degraded

Requirements:

- Each major runtime dependency and scan outcome shall map to an observable state.
- The operator shall be able to distinguish degraded-but-recovering behavior from a fully ready state.
- Controller playback API auth failures shall be distinguishable from receiver-session or receiver-visibility failures.
- Receiver-visibility failures shall be distinguishable from scan-input or payload-validation failures.
- Target-not-listed failures shall be distinguishable from playback-transfer or playback-start failures.
- The state model shall not require LED hardware to be considered complete in EPIC 3.

Related decisions: `D-2 Startup Readiness Contract`, `D-3 Supervision Model`, and `D-5 Feedback Scope`.

### FR-6 Configuration and Secret Handling Contract

EPIC 3 shall preserve headless operation and repository hygiene while making the hardened runtime maintainable after assembly.

Requirements:

- Runtime configuration shall remain supportable through a documented headless configuration path.
- No credentials or secrets shall be committed to the repository.
- The supported operational contract shall identify which configuration is required for autonomous startup and recovery validation.
- The supported operational contract shall document separate provisioning for controller-side Spotify Web API credentials and receiver-side headless OAuth or session persistence.
- The hardened runtime shall avoid depending on one-off manual steps that would be unreasonable once the device is assembled.

Related decisions: `D-1 Receiver Autonomy Strategy`, `D-2 Startup Readiness Contract`, and `D-7 Maintenance Guidance Depth`.

### FR-7 Build-Readiness Integration Constraints

EPIC 3 shall capture the runtime-related physical integration constraints that enclosure work must preserve.

Requirements:

- The EPIC 3 deliverables shall identify the scanner mounting assumptions that stable software behavior depends on.
- The EPIC 3 deliverables shall identify cable routing constraints that must be preserved for stable operation and maintainability.
- The EPIC 3 deliverables shall identify the minimum power-access and service-access assumptions needed after assembly.
- These build-readiness checkpoints shall be specific enough to guide enclosure decisions before construction starts.

Related decision: `D-6 Build-Readiness Checkpoints`.

### FR-8 Maintenance and Validation Guidance

The repository shall provide enough operational guidance that routine validation and safe troubleshooting remain practical after the device is assembled.

Requirements:

- The documentation shall define the baseline validation flow for reboot recovery, power-cycle recovery, scanner validation, receiver validation, and audio-path validation.
- The documentation shall distinguish between required baseline behavior and optional troubleshooting workarounds.
- The guidance shall help the operator distinguish controller API auth issues, receiver-visibility issues, playback-transfer issues, network-discovery issues, scanner issues, and audio-path issues.
- The guidance shall define the same-LAN discovery checks relevant to receiver visibility, including mDNS, zeroconf, and other local-network visibility assumptions when they affect diagnosis.
- Known unresolved limitations shall be recorded explicitly rather than left implicit in the workflow.

Related decisions: `D-4 Network Recovery Scope`, `D-7 Maintenance Guidance Depth`, and `D-8 Validation Depth`.

### FR-9 EPIC 2 Baseline Continuity

EPIC 3 shall harden the validated EPIC 2 baseline rather than casually reopening settled behavior.

Requirements:

- The hardened baseline shall preserve the EPIC 2 scanner intake path unless a hardening requirement forces a documented exception.
- The hardened baseline shall continue to treat USB audio as the V1 output baseline unless a documented replacement is deliberately adopted.
- The hardened baseline shall continue to support the accepted Spotify URI types and duplicate-suppression behavior already validated in earlier EPICs unless an explicit EPIC 3 exception is documented.
- Any EPIC 2 operational baseline that is replaced during hardening shall be replaced by a clearer documented baseline, not by an undocumented gap.

Related decisions: `D-1 Receiver Autonomy Strategy`, `D-6 Build-Readiness Checkpoints`, and `D-7 Maintenance Guidance Depth`.

## Non-Functional Requirements

### NFR-1 Headless Appliance Fit

The EPIC 3 solution shall remain aligned with the concept's headless appliance direction.

Requirements:

- The hardened runtime should not depend on a graphical desktop session.
- Routine operation and maintenance should remain practical over SSH or equivalent headless access.
- The hardening work should reduce operator friction rather than introduce new routine interaction complexity.

Related decisions: `D-1 Receiver Autonomy Strategy` and `D-2 Startup Readiness Contract`.

### NFR-2 Low-Maintenance Operation

The EPIC 3 baseline shall move the prototype toward normal family use rather than ongoing development-only handling.

Requirements:

- Normal use should not require ad hoc commands after reboot or power restoration.
- Recovery behavior should minimize the need for phone-side or laptop-side intervention.
- When intervention is still required, the issue should be diagnosable quickly from the documented feedback and validation flow.
- The hardening posture should acknowledge that hobbyist Spotify Connect receivers are not equivalent to an official partner appliance stack, so degraded-state behavior and recovery limits must be documented honestly.

Related decisions: `D-2 Startup Readiness Contract`, `D-3 Supervision Model`, and `D-7 Maintenance Guidance Depth`.

### NFR-3 Raspberry Pi 3 Fit

The hardening approach shall continue to respect the Raspberry Pi 3 hardware target.

Requirements:

- The runtime approach should remain lightweight enough for headless Raspberry Pi 3 operation.
- EPIC 3 should avoid unnecessary dependencies or background complexity that do not improve reliability or build readiness.
- The project should remain runnable and testable on non-Pi development machines where practical, even though EPIC 3 validation occurs on Pi hardware.

Related decision: `D-1 Receiver Autonomy Strategy`.

### NFR-4 Repeatability and Serviceability

The hardened baseline shall stay repeatable across fresh Pi setup and practical after enclosure assembly.

Requirements:

- The documented operational path should be reproducible on another fresh Pi of the same class.
- Hidden manual state should be treated as a defect in the EPIC 3 deliverable.
- The build-readiness guidance should reduce the risk that enclosure decisions block later maintenance work.

Related decisions: `D-6 Build-Readiness Checkpoints` and `D-7 Maintenance Guidance Depth`.

### NFR-5 Observability Quality

The feedback model shall be strong enough to support diagnosis during boot, recovery, and real-card validation.

Requirements:

- The operator should be able to identify whether the system is booting, degraded, ready, or failed.
- Repeated recovery attempts should remain readable rather than noisy or ambiguous.
- Successful playback readiness should be distinguishable from mere service startup.

Related decisions: `D-2 Startup Readiness Contract`, `D-5 Feedback Scope`, and `D-8 Validation Depth`.

## Acceptance Criteria

### AC-1 Repeated Clean Reboot Recovery

- Given the EPIC 3 baseline has already demonstrated a successful autonomous scan-to-playback run
- When the documented repeated clean reboot validation is performed
- Then each reboot returns the device to an autonomous ready state without another Spotify client waking the receiver
- And a fresh valid card scan can trigger playback again after each reboot
- And the result does not depend on a previously cached Spotify device ID remaining valid after reboot

### AC-2 Power-Cycle Recovery

- Given the device is in a working autonomous state
- When power is removed and restored through the documented EPIC 3 power-cycle validation flow
- Then the system returns to a usable scan-to-playback state without ad hoc launch commands or phone-side receiver activation
- And the resulting readiness or degraded state remains observable

### AC-3 Temporary Network or Spotify Availability Recovery

- Given the device has already reached a ready state
- When same-LAN Wi-Fi connectivity or Spotify-side availability is temporarily interrupted and then restored
- Then the system enters a distinguishable degraded state instead of failing silently
- And the system returns to usable scan-to-playback behavior without manual service restarts once the dependency is restored

### AC-4 Receiver Visibility Gap Diagnosis

- Given the receiver process is running but the playback target is not yet available for autonomous playback
- When the system evaluates its readiness
- Then it does not present the same ready state as a fully usable runtime
- And the operator can tell that the blocker is receiver availability rather than controller API auth, scanner input, or payload handling

### AC-5 Controller API Auth Diagnosis

- Given the receiver service is running but the controller app has invalid Spotify Web API credentials or insufficient playback scopes
- When startup or playback validation is attempted
- Then the system reports a controller-auth-specific degraded or error outcome
- And the failure is distinguishable from receiver-not-listed or network-discovery failures

### AC-6 Scanner Failure Diagnosis

- Given the Pi boots without a readable scanner device
- When startup or validation is attempted
- Then the operator sees a distinct scanner-related degraded or error outcome
- And the system does not fail silently or appear falsely ready

### AC-7 Playback Targeting Diagnosis

- Given the controller can authenticate to the Spotify Web API but the target receiver is missing, stale, or not currently listed in the device snapshot
- When playback is attempted
- Then the system refetches current receiver availability rather than relying on stale boot-time assumptions
- And the resulting device-not-listed or transfer failure is reported distinctly enough to support diagnosis

### AC-8 Audio Path Diagnosis

- Given the control path can trigger playback but the USB-audio speaker path is misconfigured or inaudible
- When the operator follows the documented EPIC 3 validation flow
- Then the workflow provides a distinct audio troubleshooting path from receiver, scanner, or network diagnosis
- And the issue is not misclassified as a malformed scan or generic controller failure

### AC-9 Build-Readiness Constraints

- Given enclosure planning is about to begin
- When the operator reviews the EPIC 3 deliverables
- Then the required scanner mounting assumptions, cable routing constraints, power access, and service access expectations are explicit enough to avoid blocking stable operation

### AC-10 Maintenance Guidance

- Given the assembled prototype needs a routine validation or basic recovery check
- When the operator follows the repository documentation
- Then the guidance is sufficient to perform the required check or safe troubleshooting step without needing source-level knowledge

### AC-11 Behavior Continuity

- Given cards and scan scenarios that already passed EPIC 2 validation
- When they are used against the hardened EPIC 3 baseline
- Then supported URI types, duplicate suppression, and baseline scan-to-playback behavior remain consistent unless an explicit EPIC 3 exception is documented

## Deliverables

- A build-ready V1 appliance baseline for Raspberry Pi 3 focused on autonomous startup, recovery, and maintainability.
- A documented operational contract for boot readiness, degraded-state behavior, and recovery expectations.
- A documented validation flow covering repeated reboot, power-cycle, network-recovery, scanner, receiver, and audio-path checks.
- A checklist of runtime-related physical integration constraints that later enclosure work must preserve.

## EPIC 4 Handoff Questions

These are not EPIC 3 blockers, but they should be captured before EPIC 4 planning starts.

### H-1 Feedback Hardware Follow-Through

This determines whether EPIC 4 should translate the EPIC 3 state model directly into hardware-visible feedback.

- [ ] Promote the EPIC 3 state model into the EPIC 4 LED or indicator baseline. (Recommended)
- [ ] Redesign the feedback model in EPIC 4
- [ ] Decide later

### H-2 Optional Control Priority

This determines which physical control should be considered first once the hardened V1 baseline exists.

- [ ] Prioritize a stop button first in EPIC 4. (Recommended)
- [ ] Prioritize richer controls such as next-track first
- [ ] Decide later

### H-3 Audio Evolution Direction

This determines how aggressively EPIC 4 should move from the stable V1 external-speaker baseline toward the concept's V2 audio direction.

- [ ] Keep the hardened V1 external-speaker baseline stable while planning internal audio as a separate EPIC 4 refinement. (Recommended)
- [ ] Begin integrated internal-audio transition immediately in EPIC 4
- [ ] Decide later

### H-4 Standalone Receiver Auth UX

This determines whether EPIC 4 should turn any remaining manual receiver bootstrap steps into a more appliance-grade maintenance flow once EPIC 3 has established a stable autonomous baseline.

- [ ] Add a documented standalone receiver-auth or re-auth flow, such as a browser-based operator UI or similarly self-contained maintenance path. (Recommended)
- [ ] Keep receiver auth as a manual bring-up procedure only
- [ ] Decide later

## Notes

- This document intentionally treats the concrete EPIC 2 findings in [docs/pi-setup-log.md](/Users/markus/Workspace/jukebox/docs/pi-setup-log.md) as baseline inputs rather than open questions.
- This document assumes the controller app's Spotify Web API credentials and the receiver service's Spotify Connect session are separate concerns that must both be handled correctly for autonomous boot behavior.
- This document intentionally does not choose a technical receiver package, supervision implementation, or module layout beyond the checked outcome-level decisions above.
- Those choices belong in `spec/EPIC-3-technical.md` after the remaining EPIC 3 decisions are taken or explicitly assumed.
- EPIC 3 should not reopen settled EPIC 2 baselines unless a hardening requirement forces a documented exception and replacement baseline.
