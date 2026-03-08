# EPIC 2 Requirements Specification

## Title

EPIC 2: Raspberry Pi Bring-Up and End-to-End V1 Playback

## Purpose

This document defines the requirements for EPIC 2 from [spec/roadmap.md](/Users/markus/Workspace/jukebox/spec/roadmap.md).
The goal is to move the validated local controller loop onto the Raspberry Pi 3 and prove the first real V1 hardware milestone: scan a physical card on the Pi and hear playback through an external speaker.

This is a requirements document, not a technical design.
It defines the behavior that must be proven in EPIC 2 and captures the product and validation choices that should be settled before a technical design is written.

## Objective

Bring up a headless Raspberry Pi OS Lite environment that can read a real USB HID scanner, run the jukebox controller service, target an on-device Spotify Connect receiver, and produce audible playback through the temporary V1 external-speaker path.

## Success Definition

EPIC 2 is complete when a Raspberry Pi 3 prototype demonstrates the following:

- The Pi can be prepared from a fresh Raspberry Pi OS Lite image using a documented headless setup flow.
- A real USB HID scanner is readable on-device and produces the expected newline-terminated Spotify URI payloads.
- A valid physical QR card scan triggers playback on the Pi's Spotify Connect receiver.
- Audio is heard through an external powered speaker connected through the V1 Pi audio path.
- A clean reboot returns the prototype to a state where another valid scan can trigger playback again without ad hoc bring-up steps.
- Remaining issues that block appliance-like reliability are documented for EPIC 3.

## Decision Checklist

Use this section to review and confirm the open product decisions for EPIC 2. Each decision includes the recommended default so the spec can be approved quickly without losing alternatives.

### D-1 Spotify Connect Receiver Baseline

EPIC 2 must converge on one supported bring-up path for the on-device Spotify Connect receiver, but the concept specification does not yet force a package-level choice.

- [x] `raspotify`
- [ ] `spotifyd`
- [ ] One documented receiver package for EPIC 2, with either `raspotify` or `spotifyd` acceptable as long as the setup guide, runtime behavior, and validation steps stay internally consistent. (Recommended)

### D-2 Pi Setup Deliverable Depth

The EPIC needs a setup outcome that is repeatable enough for continued work, but it does not necessarily need full provisioning automation yet.

- [ ] One-off bring-up notes only
- [x] A repeatable step-by-step setup procedure covering imaging, access, networking, audio, receiver bring-up, and controller bring-up. replaces `pisetup.md` (Recommended)
- [ ] Fully automated Pi provisioning and imaging flow

Note: documentation should be gathered in `docs/` rather than the root with root `README.md` acting as an entry point and index for the entire project, not just the software / pi build or development flow. The setup documentation should also distinguish between required baseline steps and optional troubleshooting workarounds, and it should avoid one-off manual steps that would prevent repeating the bring-up on a fresh Pi.

### D-3 Network Validation Baseline

The Pi needs enough network configuration to support Spotify playback and remote maintenance, but broader recovery work is intentionally deferred.

- [x] Same-LAN Wi-Fi validation only, with SSH-based setup and maintenance. (Recommended)
- [ ] Wi-Fi plus Ethernet fallback in EPIC 2
- [ ] Hotspot, captive-portal, or offline fallback flows in EPIC 2

### D-4 Boot-to-Ready Expectation

EPIC 2 must define what "basic V1 boot path" means so the milestone is more than a manually launched demo.

- [ ] Manual service start after boot is acceptable for EPIC 2
- [x] A clean boot should bring the receiver and controller into a scan-ready state through the documented V1 startup path. (Recommended)
- [ ] EPIC 2 must also include automatic recovery from degraded runtime states

### D-5 Scanner Device Binding Approach

The Pi-side scanner setup needs to be stable enough that validation does not depend on rediscovering the input device on every run.

- [ ] Operator manually selects the scanner input device on each run
- [x] EPIC 2 documents one Pi-side scanner binding approach that consistently targets the intended USB HID scanner across reboots. (Recommended)
- [ ] The controller should best-effort accept any keyboard-like input device without a defined binding rule

### D-6 LED Scope for EPIC 2

The concept includes a V1 status LED, but the roadmap explicitly defers final LED behavior while EPIC 2 focuses on the playback milestone.

- [x] No LED work in EPIC 2
- [ ] Minimal LED support for ready, scan, success, and error states if hardware is available, but LED wiring must not block the playback milestone. (Recommended)
- [ ] Final V1 LED behavior is required before EPIC 2 can complete

### D-7 Audio Output Validation Policy

The concept fixes the V1 audio baseline to the Pi audio output and allows a USB sound card only as a contingency if analog noise is unacceptable.

- [ ] EPIC 2 requires only the Pi 3.5 mm analog output path
- [x] EPIC 2 requires the Pi 3.5 mm analog output path as the default and documents a USB sound card fallback only if analog noise makes validation unusable. (Recommended)
- [ ] EPIC 2 requires a USB sound card as the baseline V1 audio path

### D-8 Playback Proof Threshold

The milestone should define whether a successful playback test stops at controller dispatch or requires proof that the real hardware output path worked end to end.

- [ ] Treat controller dispatch to the playback backend as sufficient proof
- [x] Require both an observable playback-start outcome in the software stack and audible output through the external speaker. (Recommended)
- [ ] Treat audible playback alone as sufficient proof, even if software-side confirmation is weak

Note: the test stack should be able to confirm playback sucess without relying on human hearing alone.

### D-9 Behavior Continuity from EPIC 1

EPIC 2 can either preserve the validated EPIC 1 controller behavior on Pi or reopen those choices during bring-up.

- [ ] Revisit accepted URI types, duplicate handling, and playback replacement rules during Pi bring-up
- [x] Preserve the EPIC 1 scan semantics on Pi unless a Pi-specific limitation forces a documented exception. (Recommended)
- [ ] Narrow Pi behavior to a simpler temporary subset such as track-only playback

### D-10 Reboot Validation Depth

The roadmap requires a clean reboot back to usability, but stronger hardening remains an EPIC 3 concern.

- [ ] One happy-path boot validation is enough for EPIC 2
- [x] EPIC 2 must include at least one repeatable clean-reboot validation that returns the Pi to scan-ready state without ad hoc commands. (Recommended)
- [ ] EPIC 2 must include repeated power-loss and soak testing

Note: Deployment to the Pi should work in a scripted way and be accessible for the agent workflow for automated testing and deployment. It should rely on ssh and scp rather than requiring physical access to the SD card after the initial image is prepared, but it does not need to be fully automated yet.

### D-11 Configuration and Secret Handling

Spotify-related setup will require credentials or account-linked configuration, and EPIC 2 must define how that happens without weakening the repository hygiene.

- [ ] Rely on ad hoc local credential handling outside the documented setup flow
- [x] Use a documented headless configuration path that keeps secrets out of the repository and out of committed files. (Recommended)
- [ ] Defer configuration and credential handling details until EPIC 3

## In Scope

- Headless Raspberry Pi OS Lite bring-up for Raspberry Pi 3.
- Baseline SSH access and networking needed for development and validation.
- On-device USB HID scanner intake using a real scanner.
- Spotify Connect receiver bring-up on the Pi.
- Running the controller service on the Pi against real scanner input.
- External powered speaker playback through the V1 Pi audio path.
- Basic boot-to-ready and clean-reboot validation.
- Observable feedback and diagnostics sufficient to validate the hardware loop.
- Setup and operator documentation needed to reproduce the EPIC 2 prototype.

## Out of Scope

- Long-run recovery behavior beyond the clean-reboot baseline needed for EPIC 2.
- Stronger service supervision or self-healing policies intended for appliance hardening.
- Final LED behavior, optional stop button behavior, or richer physical controls.
- Internal speakers, amplifier integration, or other V2 audio work.
- Enclosure refinements that do not block functional Pi testing.
- Local-media fallback, queue mode, or other future playback extensions.
- OTA update strategy, read-only filesystem mode, or similar post-bring-up hardening work.

## Functional Requirements

### FR-1 Pi Runtime Baseline

EPIC 2 shall establish the minimum Pi runtime environment required for headless V1 playback validation.

Requirements:

- The prototype shall run on Raspberry Pi OS Lite on a Raspberry Pi 3.
- Initial setup and routine maintenance shall be possible without requiring a desktop environment on the Pi.
- The setup flow shall define the minimum networking, remote-access, and device-access prerequisites needed to reach a scan-ready state.
- The setup flow shall avoid undocumented one-off machine state that would prevent repeating the bring-up on a fresh Pi.

Related decisions: `D-2 Pi Setup Deliverable Depth`, `D-3 Network Validation Baseline`, and `D-11 Configuration and Secret Handling`.

### FR-2 On-Device Scanner Intake

The Pi prototype shall consume input from a real USB HID scanner and treat the scanner as the source of QR payloads.

Requirements:

- The controller shall accept newline-terminated scan payloads from the scanner on-device.
- The Pi setup shall define how the intended scanner input source is identified consistently.
- Empty lines shall be ignored.
- A missing or unreadable scanner shall produce an observable failure state rather than silent non-response.

Related decision: `D-5 Scanner Device Binding Approach`.

### FR-3 Scan Semantics Carried Forward from EPIC 1

EPIC 2 shall preserve the validated V1 scan behavior unless the Pi environment forces a documented exception.

Requirements:

- The Pi prototype shall accept Spotify URI payloads as the card content format.
- The Pi prototype shall support `spotify:track:<id>`, `spotify:album:<id>`, and `spotify:playlist:<id>`.
- Duplicate scans shall continue to be suppressed according to the EPIC 1 baseline rather than retriggering playback immediately.
- A new valid scan shall replace the prior playback intent instead of being queued.

Related decision: `D-9 Behavior Continuity from EPIC 1`.

### FR-4 Spotify Receiver Availability

The Pi shall expose an on-device Spotify Connect playback target that the controller can use during validation.

Requirements:

- EPIC 2 shall define one supported receiver bring-up path for the prototype.
- The receiver shall be verifiable as available before scan validation begins.
- Receiver unavailability shall produce an observable failure outcome instead of an ambiguous no-playback state.
- The chosen receiver path shall fit the headless Pi runtime baseline.

Related decision: `D-1 Spotify Connect Receiver Baseline`.

### FR-5 End-to-End Playback Triggering

A valid physical card scan on the Pi shall produce the expected playback action all the way through the V1 hardware path.

Requirements:

- A valid accepted scan shall trigger playback targeting the configured on-device receiver.
- The controller shall expose a visible accepted-scan outcome and a visible playback-start or playback-failed outcome.
- A second different valid scan shall replace the previous playback intent with the latest one.
- The EPIC 2 success path shall not stop at parse success alone; it shall prove that the playback path was actually exercised.

Related decisions: `D-8 Playback Proof Threshold` and `D-9 Behavior Continuity from EPIC 1`.

### FR-6 Audio Output Path

The EPIC 2 prototype shall use the V1 external-speaker audio path defined by the concept specification.

Requirements:

- Audio playback shall be validated through an external powered speaker connected to the Raspberry Pi audio output path.
- The baseline EPIC 2 success target shall use the Pi 3.5 mm analog output path.
- If analog output quality is poor enough to block meaningful validation, the issue shall be documented clearly rather than silently worked around.
- Any USB sound card fallback used during EPIC 2 shall be treated as a documented exception to the baseline, not as an undeclared change in product direction.

Related decision: `D-7 Audio Output Validation Policy`.

### FR-7 Basic Boot-to-Ready Path

EPIC 2 shall define and validate the minimum acceptable boot behavior for the working Pi prototype.

Requirements:

- The prototype shall have a documented path from power-on or clean reboot to scan-ready operation.
- A clean reboot shall return the Pi to a state where another valid scan can trigger playback without ad hoc manual commands.
- Any manual preconditions that remain necessary during EPIC 2 shall be explicit in the setup and validation documentation.
- Stronger recovery expectations beyond the clean-reboot baseline shall be deferred to EPIC 3.

Related decisions: `D-4 Boot-to-Ready Expectation` and `D-10 Reboot Validation Depth`.

### FR-8 Feedback and Diagnostics

The Pi prototype shall expose enough feedback that a failed hardware test can be diagnosed without guessing.

Required observable states:

- Booting or not ready
- Ready for scan
- Scan received
- Valid scan accepted
- Duplicate suppressed
- Invalid payload
- Unsupported content type
- Playback started
- Playback failed
- Scanner unavailable
- Receiver unavailable

Requirements:

- Each scan event shall be traceable to an observable final outcome.
- The operator shall be able to distinguish scanner issues, payload issues, and playback issues.
- If LED hardware is present during EPIC 2, LED behavior may mirror a subset of these states, but lack of LED wiring shall not hide software-side feedback.

Related decisions: `D-6 LED Scope for EPIC 2` and `D-8 Playback Proof Threshold`.

### FR-9 Setup and Operations Documentation

EPIC 2 shall produce enough documentation that the Pi prototype can be repeated and maintained during further development.

Requirements:

- The repository shall include a baseline setup procedure for imaging, access, networking, receiver bring-up, controller bring-up, and validation.
- The documented flow shall identify the expected verification points for scanner readiness, receiver readiness, and audio readiness.
- The operator documentation shall capture any known EPIC 2 caveats that remain unresolved.
- The documentation shall distinguish between required baseline steps and optional troubleshooting workarounds.

Related decisions: `D-2 Pi Setup Deliverable Depth`, `D-7 Audio Output Validation Policy`, and `D-11 Configuration and Secret Handling`.

### FR-10 Secret Hygiene

EPIC 2 shall preserve repository hygiene while enabling headless bring-up of the playback stack.

Requirements:

- No credentials or secrets shall be committed to the repository.
- The documented setup flow shall identify how runtime configuration is provided without embedding secrets in tracked files.
- Developer convenience shall not depend on fake Spotify credentials or placeholder production secrets.

Related decision: `D-11 Configuration and Secret Handling`.

## Non-Functional Requirements

### NFR-1 Headless Simplicity

The EPIC 2 prototype shall remain aligned with the concept's headless appliance direction.

Requirements:

- The Pi runtime should not depend on a graphical desktop session.
- The bring-up flow should be practical over SSH.
- The prototype should avoid adding operator-facing complexity that does not improve validation of the QR-to-playback loop.

Related decisions: `D-2 Pi Setup Deliverable Depth` and `D-3 Network Validation Baseline`.

### NFR-2 Raspberry Pi 3 Fit

The EPIC 2 solution shall respect the Raspberry Pi 3 hardware target.

Requirements:

- The chosen runtime approach should remain lightweight enough for Raspberry Pi 3 headless operation.
- The EPIC should avoid unnecessary background services or tooling that do not contribute directly to Pi bring-up or playback validation.
- The prototype should remain runnable and testable on non-Pi development machines where practical, even though EPIC 2 validation occurs on Pi hardware.

Related decision: `D-1 Spotify Connect Receiver Baseline`.

### NFR-3 Repeatability

The EPIC 2 setup outcome shall be repeatable enough to support continued development.

Requirements:

- The documented bring-up should be sufficient to reproduce the prototype on another fresh Pi of the same class.
- Hidden manual steps should be treated as defects in the EPIC 2 deliverable.
- The setup should converge on one baseline path rather than multiple partially documented alternatives.

Related decisions: `D-2 Pi Setup Deliverable Depth` and `D-5 Scanner Device Binding Approach`.

### NFR-4 Observability Quality

The Pi prototype shall make diagnosis practical during hardware testing.

Requirements:

- The operator should be able to identify where a failed run stopped.
- Feedback should remain readable during repeated scans and reboots.
- A successful scan should be distinguishable from a merely received scan.

Related decisions: `D-6 LED Scope for EPIC 2` and `D-8 Playback Proof Threshold`.

## Acceptance Criteria

### AC-1 Headless Bring-Up

- Given a freshly prepared Raspberry Pi OS Lite image on a Raspberry Pi 3
- When the operator follows the documented EPIC 2 setup flow
- Then the Pi becomes reachable for headless setup and maintenance
- And the documented flow is sufficient to reach the prototype's baseline runtime state without requiring a desktop environment

### AC-2 Valid Track Card Scan on Pi

- Given the Pi is in a ready state with the scanner attached, the receiver available, and an external powered speaker connected
- When a physical card containing a valid `spotify:track:<id>` QR payload is scanned
- Then the controller accepts the scan
- And the playback path is triggered on the Pi receiver
- And audio is heard through the external speaker

### AC-3 Valid Album or Playlist Card Scan on Pi

- Given the Pi is in a ready state with the scanner attached, the receiver available, and an external powered speaker connected
- When a physical card containing a valid `spotify:album:<id>` or `spotify:playlist:<id>` QR payload is scanned
- Then the controller accepts the scan
- And the corresponding playback path is triggered
- And audio is heard through the external speaker

### AC-4 Duplicate Suppression on Pi

- Given a valid card has just been accepted on the Pi
- When the same card is scanned again within the configured duplicate window
- Then the controller does not trigger a second playback start
- And it emits an observable duplicate-suppressed outcome

### AC-5 New Valid Scan Replaces Prior Playback Intent

- Given one valid card has already been accepted
- When a different valid card is scanned
- Then the new scan is accepted immediately
- And the latest playback intent replaces the prior one rather than being queued

### AC-6 Invalid or Unsupported Scan on Pi

- Given the Pi is ready for scans
- When a malformed payload or unsupported Spotify URI type is scanned
- Then no playback is started
- And the operator sees an observable invalid-payload or unsupported-content outcome
- And the controller remains available for the next scan

### AC-7 Clean Reboot Recovery

- Given the Pi prototype has already demonstrated a successful scan-to-playback run
- When the Pi is cleanly rebooted
- Then the receiver and controller return to the documented ready state
- And another valid card scan can trigger playback again without ad hoc manual launch commands

### AC-8 Missing Scanner or Receiver Diagnosis

- Given the Pi is booted but either the scanner is unavailable or the receiver is not ready
- When the operator attempts to validate a scan
- Then the failure is surfaced as a distinguishable observable state
- And the operator does not have to infer the fault from silent no-playback behavior

## Deliverables

- A Raspberry Pi 3 prototype that demonstrates physical scan to audible playback through the V1 external-speaker path.
- A documented baseline setup procedure for Pi imaging, remote access, networking, scanner intake, receiver bring-up, controller bring-up, and audio validation.
- A documented basic boot-to-ready and clean-reboot validation flow.
- A recorded list of unresolved reliability and recovery gaps for EPIC 3.

## EPIC 3 Handoff Questions

These are not EPIC 2 blockers, but they should be captured before EPIC 3 technical planning starts.

### H-1 Service Supervision Direction

This determines whether EPIC 3 should harden the EPIC 2 startup model in place or replace it.

- [ ] Harden the EPIC 2 startup and supervision path in place. (Recommended)
- [ ] Replace the startup and supervision path in EPIC 3
- [ ] Decide later

### H-2 Recovery Expectations Beyond Clean Reboot

This determines how much unattended recovery EPIC 3 must deliver for power loss, receiver restarts, and network interruptions.

- [ ] Add explicit recovery expectations for power loss, network drops, and service restarts in EPIC 3. (Recommended)
- [ ] Treat those behaviors as best effort only
- [ ] Decide later

### H-3 Feedback Evolution

This determines whether the observable states used in EPIC 2 should become the basis for the later appliance feedback model.

- [ ] Promote the EPIC 2 observable state set into the EPIC 3 appliance feedback baseline. (Recommended)
- [ ] Redesign the feedback model in EPIC 3
- [ ] Decide later

### H-4 V1 Audio Baseline Stability

This determines whether the analog audio path remains the V1 baseline after Pi bring-up or whether EPIC 3 must treat audio hardware changes as required.

- [ ] Keep the Pi analog audio path as the V1 baseline unless EPIC 2 uncovered a blocking issue. (Recommended)
- [ ] Promote USB audio hardware to required V1 baseline
- [ ] Decide later

## Notes

- This document intentionally does not lock in a package-level Spotify receiver choice yet.
- This document intentionally does not define the technical implementation shape of the Pi controller runtime, module layout, or configuration files.
- Those choices belong in `spec/EPIC-2-technical.md` after the EPIC 2 decisions are taken or explicitly assumed.
