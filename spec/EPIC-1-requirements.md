# EPIC 1 Requirements Specification

## Title

EPIC 1: Local Core Loop Validation

## Purpose

This document defines the requirements for EPIC 1 from [spec/roadmap.md](/Users/markus/Workspace/jukebox/spec/roadmap.md).
The goal is to validate the core QR-to-playback loop locally before Raspberry Pi deployment work begins.

This is a requirements document, not a technical design.
It defines the behavior that must be proven in EPIC 1 and captures the main product choices that should be settled now.

## Objective

Prove that a scanned QR payload can be accepted locally, parsed as a supported Spotify URI, filtered for accidental duplicate scans, routed to the correct playback action, and surfaced through clear observable feedback.

## Success Definition

EPIC 1 is complete when a local prototype demonstrates the following:

- A newline-terminated scan payload reaches the controller loop reliably.
- Valid Spotify URIs are recognized and routed to the expected playback path.
- Duplicate scans within the configured short window do not trigger repeated playback actions.
- Invalid scans fail safely and surface an observable error outcome.
- The overall response is fast enough to feel immediate in the intended child-first interaction.

## Decision Checklist

Use this section to review and confirm the open product decisions for EPIC 1. Each decision includes the recommended default so the spec can be approved quickly without losing alternatives.

### D-1 Scan Input Coverage

EPIC 1 should optimize for fast local iteration without losing sight of the scanner behavior that later hardware work depends on.

- [ ] Emulated keyboard input only
- [ ] USB scanner only
- [x] Both emulated keyboard input and USB scanner (Recommended)

### D-2 Accepted Payload Format

The safest baseline is to accept only the payload format the cards are expected to contain unless broader parsing adds clear value.

- [x] Spotify URI only (Recommended)
- [ ] Spotify URI plus Spotify web URLs
- [ ] Best-effort arbitrary text parsing

### D-3 Supported Spotify URI Types

EPIC 1 should cover enough content types to validate the intended V1 jukebox behavior without expanding the initial surface area unnecessarily.

- [ ] Track only
- [x] Track + Album + Playlist (Recommended)
- [ ] Track + Album + Playlist + Artist

### D-4 Playback Validation Depth

The local prototype needs to prove dispatch behavior, but it does not necessarily need to depend on a live Spotify environment to do that.

- [ ] Stubbed playback action with observable output (Recommended)
- [x] Stubbed playback plus optional real Spotify trigger. The real trigger is the validation target, the stubbed action is just a fallback for development/tests when Spotify integration is not available. (Recommended)
- [ ] Real Spotify trigger only

### D-5 Duplicate Suppression Window

The duplicate window should be long enough to catch accidental repeat scans but short enough not to block intentional rescans.

- [ ] 1 second
- [x] 2 seconds (Recommended)
- [ ] 3 seconds

### D-6 Duplicate Match Rule

This decision defines what counts as "the same scan" during the duplicate suppression window.

- [x] Exact payload after newline trimming. (Recommended)
- [ ] Normalized URI match
- [ ] Type-and-ID-only match

### D-7 Playback Policy for a New Valid Scan

When a second valid card is scanned, the system needs a consistent rule for whether the latest scan replaces or defers to the current playback intent.

- [ ] Ignore new scan while already playing
- [x] Replace current playback intent with latest scan. If it's the same as the current playback, do nothing. (Recommended)
- [ ] Queue the new scan

### D-8 Feedback Surface

EPIC 1 needs feedback that is easy to observe during development without introducing interface work that is outside the scope of local validation.

- [ ] Structured logs only
- [x] Terminal status plus structured logs (Recommended)
- [ ] Local GUI or web UI

### D-9 Error Detail Level

Errors should be specific enough to support debugging but not so verbose that normal test runs become noisy.

- [ ] Generic invalid scan message only
- [x] Reason code plus human-readable message (Recommended)
- [ ] Verbose debug-only output

### D-10 Recoverable Error Behavior

Recoverable failures during EPIC 1 should favor continued validation unless there is a strong reason to stop the loop.

- [ ] Exit on first recoverable error
- [x] Continue processing after recoverable errors (Recommended)
- [ ] Auto-restart wrapper during EPIC 1

### D-11 Local Workflow Target

The EPIC should define the minimum local workflow that makes iteration and repeatable validation practical.

- [ ] Manual run only
- [x] Single local run command plus automated tests (Recommended)
- [ ] Containerized workflow from day one

### D-12 Automated Test Scope

The automated tests should cover the highest-value logic that can be validated without physical hardware.

- [ ] Parser only
- [x] Parser + routing + duplicate suppression (Recommended)
- [ ] Manual tests only

### D-13 Responsiveness Target

The project needs a concrete threshold for "feels immediate" so responsiveness is judged consistently during local validation.

- [ ] Best effort only
- [x] Visible acknowledgement within 250 ms and playback dispatch feedback within 1 second (Recommended)
- [ ] Visible acknowledgement and dispatch feedback both within 500 ms

### D-14 EPIC 1 Implementation Posture

EPIC 1 should stay lightweight, but the prototype can still be structured so EPIC 2 does not have to throw away the core controller logic.

- [ ] Throwaway prototype
- [x] Lightweight but forward-compatible prototype (Recommended)
- [ ] Production-grade local system

### D-15 Observability Output Style

Observability should balance human readability during manual testing with enough structure to support debugging and later automation.

- [ ] Minimal human-readable output only
- [x] Structured event output plus readable terminal state (Recommended)
- [ ] Structured output only

## In Scope

- Local scan intake on a development machine.
- Emulated scanner input for fast iteration.
- Optional direct USB scanner validation on the development machine when hardware is available.
- URI parsing and validation for the supported Spotify content types.
- Duplicate-scan suppression.
- Playback dispatch validation through a local observable action.
- Observable feedback for normal, duplicate, and error flows.
- Minimal automated verification for the controller logic.

## Out of Scope

- Raspberry Pi deployment, imaging, service supervision, and startup behavior.
- GPIO, LEDs, buttons, or any wiring-specific integration.
- Production Spotify Connect receiver setup on Raspberry Pi.
- Wi-Fi resilience, power-loss recovery, or appliance-hardening work.
- Enclosure design decisions beyond what is already captured in the concept and roadmap.

## Functional Requirements

### FR-1 Scan Intake

The EPIC 1 prototype shall accept scan input as newline-terminated text and treat each completed line as one scan event.

Requirements:

- The controller shall process one completed payload per newline.
- The controller shall support local emulated input so development can proceed without requiring scanner hardware for every iteration.
- The controller shall be able to consume real USB scanner input on a development machine without changing the core controller behavior.
- The controller shall ignore empty lines.

Related decision: `D-1 Scan Input Coverage`.

### FR-2 Payload Validation

The controller shall validate the scanned payload before attempting playback dispatch.

Requirements:

- The controller shall trim trailing newline and carriage-return characters only.
- The controller shall reject empty or malformed payloads.
- The controller shall treat the scanned payload as the source of truth and shall not attempt fuzzy recovery from obviously invalid input.
- The controller shall keep processing future scans after an invalid payload.

Related decision: `D-2 Accepted Payload Format`.

### FR-3 Supported Content Types

The controller shall support the minimum useful Spotify URI set for V1 behavior validation.

Requirements:

- The controller shall recognize `spotify:track:<id>`.
- The controller shall recognize `spotify:album:<id>`.
- The controller shall recognize `spotify:playlist:<id>`.
- Unsupported but well-formed Spotify URI types shall produce a clear unsupported-content outcome rather than a crash or silent success.

Related decision: `D-3 Supported Spotify URI Types`.

### FR-4 Duplicate-Scan Suppression

The controller shall suppress accidental repeated scans of the same card within a short time window.

Requirements:

- The controller shall compare each new valid payload against the most recent accepted valid payload.
- If the same payload is received again within the configured duplicate window, the controller shall not trigger playback again.
- A suppressed duplicate shall still produce an observable duplicate outcome.
- Once the duplicate window has expired, the same payload may trigger playback again.

Related decisions: `D-5 Duplicate Suppression Window` and `D-6 Duplicate Match Rule`.

### FR-5 Playback Dispatch

The controller shall route each accepted valid scan to the expected playback action path.

Requirements:

- EPIC 1 shall prove correct dispatch behavior locally without depending on Raspberry Pi integration.
- A valid accepted scan shall produce a distinct playback-trigger event.
- The dispatch behavior shall preserve the recognized Spotify content type so downstream playback handling can differ if needed later.
- A new accepted valid scan shall replace the prior playback intent rather than being queued.

Related decisions: `D-4 Playback Validation Depth` and `D-7 Playback Policy for a New Valid Scan`.

### FR-6 Observable Feedback

The prototype shall expose enough feedback to make every major controller outcome visible during local validation.

Required observable states:

- Idle
- Scan received
- Valid scan accepted
- Duplicate suppressed
- Invalid payload
- Unsupported content type
- Playback dispatch succeeded
- Playback dispatch failed

Requirements:

- Each state transition shall be visible during a local run.
- The operator shall be able to distinguish duplicate suppression from invalid input handling.
- Feedback shall be understandable without reading source code.

Related decisions: `D-8 Feedback Surface` and `D-9 Error Detail Level`.

### FR-7 Failure Safety

The controller shall fail safely for recoverable runtime issues encountered during EPIC 1 validation.

Requirements:

- Invalid payloads shall not terminate the controller loop.
- Unsupported content types shall not terminate the controller loop.
- Recoverable playback dispatch failures shall surface a failure outcome and keep the controller available for the next scan.
- Any unrecoverable failure shall be obvious to the operator.

Related decision: `D-10 Recoverable Error Behavior`.

### FR-8 Local Workflow and Testability

EPIC 1 shall establish a lightweight workflow that supports quick iteration on the controller logic.

Requirements:

- The prototype shall be runnable locally through a simple documented command.
- The repository shall include automated tests for the core logic that does not require physical scanner hardware.
- The automated coverage shall include payload validation, supported-type routing, and duplicate suppression behavior.
- The local validation flow shall support manual replay of representative scan payloads.

Related decisions: `D-11 Local Workflow Target` and `D-12 Automated Test Scope`.

## Non-Functional Requirements

### NFR-1 Responsiveness

The local prototype shall feel immediate enough to support the intended child-first interaction.

Requirements:

- Observable scan acknowledgement should appear effectively immediately after a payload is completed.
- Playback dispatch feedback should appear quickly enough that the operator can tell the system responded without ambiguity.
- The EPIC should explicitly reject a solution that feels sluggish during repeated manual validation.

Related decision: `D-13 Responsiveness Target`.

### NFR-2 Simplicity

The EPIC 1 solution shall remain intentionally lightweight.

Requirements:

- The prototype shall avoid introducing Raspberry Pi-specific infrastructure concerns.
- The prototype shall avoid complex UI work that does not improve validation of the core loop.
- The prototype shall favor decisions that can carry forward into EPIC 2 without forcing a full rewrite of the core logic.

Related decision: `D-14 EPIC 1 Implementation Posture`.

### NFR-3 Observability Quality

The prototype shall produce outputs that make debugging practical during development.

Requirements:

- Each scan event should be traceable to a final outcome.
- Logs or terminal output should include enough context to distinguish parse failures, duplicate suppression, and playback dispatch failures.
- The output should remain readable during repeated scans.

Related decision: `D-15 Observability Output Style`.

## Acceptance Criteria

### AC-1 Valid Track Scan

- Given a valid `spotify:track:<id>` payload
- When the payload is scanned locally
- Then the controller accepts it
- And emits a visible accepted-scan outcome
- And emits a visible playback-trigger outcome

### AC-2 Valid Album Scan

- Given a valid `spotify:album:<id>` payload
- When the payload is scanned locally
- Then the controller routes it through the album playback path
- And emits a visible playback-trigger outcome

### AC-3 Valid Playlist Scan

- Given a valid `spotify:playlist:<id>` payload
- When the payload is scanned locally
- Then the controller routes it through the playlist playback path
- And emits a visible playback-trigger outcome

### AC-4 Duplicate Suppression

- Given a valid payload has just been accepted
- When the same payload is scanned again within the duplicate window
- Then the controller does not emit a second playback-trigger outcome
- And emits a visible duplicate-suppressed outcome

### AC-5 Duplicate Expiry

- Given a valid payload has previously been accepted
- When the same payload is scanned again after the duplicate window expires
- Then the controller accepts it again
- And emits a new playback-trigger outcome

### AC-6 Invalid Payload

- Given a malformed or non-Spotify payload
- When it is scanned locally
- Then the controller emits a visible invalid-payload outcome
- And does not emit a playback-trigger outcome
- And remains available for the next scan

### AC-7 Unsupported Spotify Type

- Given a well-formed but unsupported Spotify URI type
- When it is scanned locally
- Then the controller emits a visible unsupported-content outcome
- And does not emit a playback-trigger outcome

### AC-8 Consecutive Different Valid Scans

- Given one valid payload has already been accepted
- When a different valid payload is scanned
- Then the new payload is accepted immediately
- And the controller emits a new playback-trigger outcome for the latest scan

### AC-9 Local Workflow

- Given a development machine without attached scanner hardware
- When the developer runs the documented local workflow
- Then the core scan-to-playback logic can be validated through emulated input
- And automated tests cover the core parsing and duplicate-suppression logic

## Deliverables

- A local prototype that proves the scan-to-playback control loop.
- A documented baseline for valid scan, duplicate scan, invalid scan, and unsupported-content behavior.
- Automated tests for the core controller rules that do not require Raspberry Pi hardware.
- A short list of EPIC 2 handoff questions that should be answered when moving onto Raspberry Pi.

## EPIC 2 Handoff Questions

These are not EPIC 1 blockers, but they should be captured before EPIC 2 technical planning starts.

### H-1 Production Input Abstraction Direction

This determines whether the EPIC 1 input contract becomes the starting point for the Raspberry Pi integration layer.

- [ ] Promote the EPIC 1 controller input contract directly into EPIC 2 (Recommended)
- [ ] Rewrite input handling during Pi bring-up
- [ ] Decide later

### H-2 Feedback Mapping Direction

This determines whether the observable states proven in EPIC 1 should map directly onto the later LED state model.

- [ ] Map EPIC 1 observable states to future LED states in EPIC 2 (Recommended)
- [ ] Redesign the state set in EPIC 2
- [ ] Decide later

### H-3 Playback Adapter Evolution

This determines whether EPIC 2 should preserve the EPIC 1 dispatch contract and only swap the backend implementation.

- [ ] Keep the EPIC 1 dispatch contract and swap the backend in EPIC 2 (Recommended)
- [ ] Replace the dispatch model entirely in EPIC 2
- [ ] Decide later

## Notes

- This document intentionally does not choose the production Spotify playback stack for Raspberry Pi.
- This document intentionally does not lock in implementation language, process model, or deployment mechanics.
- Those decisions belong in the EPIC 1 technical specification if and when the team needs them.
