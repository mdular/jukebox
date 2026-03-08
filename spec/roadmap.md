# QR Card Jukebox Roadmap

## Summary

This roadmap turns the concept in [spec/concept.md](/Users/markus/Workspace/jukebox/spec/concept.md) into four incremental EPICs.
The sequence is intentional: prove the core interaction locally first, move it onto the Raspberry Pi second, harden it into a dependable appliance third, and add polish only after the base system is stable enough for a day-one family build.

This document is intentionally decision-light.
Its purpose is to define the build order, validation milestones, and expected outputs for each EPIC so that detailed requirements and technical specifications can be written later.

## Roadmap Principles

- Validate the core QR-to-playback loop before committing to Raspberry Pi integration details.
- Treat V1 external-speaker playback as the first real-world success target.
- Prioritize reliability, recovery, and low maintenance before adding polish or extra controls.
- Include hardware-related work only when it affects software behavior, Pi setup, or readiness for the physical build.
- Defer detailed implementation choices, part selection, and interface specifics to the per-EPIC requirements and technical spec documents.

## EPIC 1: Local Core Loop Validation

### Objective

Prove the core interaction without Raspberry Pi dependency: a scanned QR payload is accepted, parsed as a Spotify URI, and translated into the expected playback action with clear system feedback.

### Scope

- Validate scanner input handling locally, either through emulated input or direct USB scanner testing on a development machine.
- Define the smallest usable controller loop for scan intake, URI parsing, duplicate-scan suppression, and playback triggering.
- Represent playback feedback states in a lightweight way, such as logs, terminal output, or simple stubs.
- Confirm the expected behavior for the main content types in scope for V1, centered on Spotify URIs.
- Establish the minimum development workflow needed to iterate on the controller logic quickly.

### Validation Focus

- A valid scan reaches the controller loop and is recognized consistently.
- Supported Spotify URIs are parsed and routed to the expected playback trigger path.
- Duplicate scans within a short interval do not create repeated playback actions.
- Invalid or malformed scans fail safely and surface an observable error state.
- The end-to-end interaction feels fast enough to support the intended child-friendly UX.

### Outputs

- A validated local prototype of the scan-to-playback control loop.
- A defined V1 behavior baseline for valid scans, duplicate scans, and invalid scans.
- A short list of open questions that only become relevant once the flow moves onto Raspberry Pi hardware.

### Deferred Decisions

- Raspberry Pi deployment model, startup behavior, and service supervision.
- GPIO integration, LED wiring details, and button handling.
- Wi-Fi resilience, power-loss recovery, and unattended restart behavior.
- Enclosure design, scanner mounting geometry, and internal audio decisions.

## EPIC 2: Raspberry Pi Bring-Up and End-to-End V1 Playback

### Objective

Move the validated core loop onto the Raspberry Pi 3 and reach a real V1 playback milestone: scan a physical card on the Pi and hear playback through an external speaker.

### Scope

- Prepare Raspberry Pi OS Lite for headless operation and development access.
- Establish the baseline Pi runtime environment, including networking and device access needed for the scanner and audio output.
- Set up a Spotify Connect receiver on the Pi and confirm it can act as the playback target.
- Run the controller service on the Pi and connect it to real USB scanner input.
- Use the temporary V1 audio path with an external powered speaker through the Pi's USB sound card.
- Define the expected boot-to-ready path for the software stack at a basic V1 level.

### Validation Focus

- The Raspberry Pi boots into a usable environment without requiring ad hoc manual setup steps.
- The scanner is readable on-device and produces the expected payload format.
- The controller service can translate a real scan into playback on the configured Spotify receiver.
- Audio plays through the external speaker path with acceptable baseline reliability for concept validation.
- A clean reboot returns the device to a state where another scan can trigger playback again.

### Outputs

- A Raspberry Pi prototype that demonstrates the full V1 concept with real hardware in the loop.
- A baseline setup procedure for Pi imaging, access, networking, audio, and playback service bring-up.
- A clear list of issues that must be solved before the system can be considered appliance-like.

### Deferred Decisions

- Long-run recovery behavior and stronger service supervision policies.
- Final LED behavior and any optional physical controls beyond what is needed for basic V1 validation.
- Internal speaker architecture, amplifier choice, and V2 audio integration.
- Physical enclosure refinements that do not block functional Pi testing.

## EPIC 3: Appliance Hardening and Build Readiness

### Objective

Turn the working Pi prototype into a stable, low-maintenance appliance candidate that is ready to be built into the enclosure and expected to work on day one with minimal intervention.

### Scope

- Harden startup, restart, and recovery behavior for normal family use.
- Define the expected service supervision model for the controller and playback stack.
- Improve resilience around power loss, reboots, and network reconnection.
- Formalize system feedback for idle, scan, playback success, and recoverable error states.
- Add the hardware-adjacent checkpoints needed to support enclosure integration, including scanner mounting assumptions, cable routing, power access, and serviceability.
- Capture the minimum operational guidance required to keep the device maintainable after assembly.

### Validation Focus

- Repeated reboot and power-cycle tests return the device to a usable state without manual recovery.
- Expected network interruptions recover cleanly enough for normal household use.
- Failure states are observable and distinguishable enough to support quick diagnosis.
- The software and Pi setup no longer depend on fragile development-only steps.
- Build-related checkpoints are specific enough to avoid enclosure decisions that would block the stable runtime.

### Outputs

- A build-ready V1 appliance baseline focused on robustness rather than feature growth.
- An agreed set of reliability expectations for startup, recovery, and normal operation.
- A checklist of physical integration constraints that later enclosure work must preserve.

### Deferred Decisions

- Premium UX refinements that do not improve baseline reliability.
- Internal stereo implementation and acoustic tuning.
- Expanded control surface such as next-track or richer interaction modes.
- Future playback modes, including local media fallback and queue-oriented behavior.

## EPIC 4: Polish and V2-Oriented Enhancements

### Objective

Add refinement after the stable V1 appliance baseline exists, while keeping the core interaction simple and preserving the low-maintenance characteristics established in EPIC 3.

### Scope

- Refine user-facing feedback behavior, especially around LED signaling and perceived responsiveness.
- Introduce optional controls that fit the concept without increasing operational complexity, such as a stop button.
- Define the direction for volume control and the transition from external V1 audio to a more integrated V2 audio approach.
- Improve maintenance ergonomics where they reduce friction without destabilizing the core loop.
- Separate immediate polish work from longer-term backlog concepts so V2 planning stays disciplined.

### Validation Focus

- Added controls or feedback improvements make the device clearer to use without confusing the child-first interaction model.
- The polished experience still boots, recovers, and operates as reliably as the hardened V1 baseline.
- Any V2-oriented work does not reintroduce complexity that should remain deferred.
- The roadmap clearly distinguishes polish from net-new feature expansion.

### Outputs

- A more finished appliance experience built on top of the stable V1 foundation.
- A clear bridge from validated V1 behavior to the concept's V2 direction for audio and controls.
- A labeled post-roadmap backlog for ideas that remain intentionally out of scope.

### Parking lot for ideas

- automatic WiFi fallback network
- OTA updates via git pull
- read-only filesystem mode (very useful for appliance devices)
- generator for the printer-friendly QR card sheets, using song metadata and artwork. should convert spotify links into URI format.
- cards for setup and stop actions
- align scanner-ready lights/beeps with actual service readiness so the hardware does not appear ready before the jukebox services are usable
- auto-shutdown after a long idle period, with a simple physical power-on to recover without needing to explain shutdown vs restart semantics to family members


### Deferred Decisions

- Detailed internal speaker selection, amplifier integration, and enclosure acoustics.
- Local playback fallback implementation details and media mapping behavior.
- Queue mode, story cards, podcast cards, and other feature expansions beyond the core jukebox loop.
- Any companion configuration tooling or broader management interface.

## Sequencing Notes

- EPIC 1 must finish before EPIC 2 begins in earnest because the local controller loop is the cheapest place to validate core behavior.
- EPIC 2 establishes the first real-world success milestone: physical scan to playback on Raspberry Pi with external speakers.
- EPIC 3 is the release gate for enclosure build readiness; polish work should not overtake it.
- EPIC 4 should only start once the system is already dependable enough to be treated as an appliance rather than a prototype.

## Assumptions

- The concept specification in [spec/concept.md](/Users/markus/Workspace/jukebox/spec/concept.md) is the source of truth for this roadmap.
- The roadmap is limited to software and Raspberry Pi setup, with hardware included only where it affects validation or build readiness.
- Detailed implementation choices, acceptance thresholds, and component selections will be made in later requirements and technical specification documents for each EPIC.
