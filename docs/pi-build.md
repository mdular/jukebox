# Raspberry Pi Build and Parts

This document records the current prototype parts and hardware notes that affect software behavior, setup, or build readiness.
It is intentionally light on enclosure construction detail.

Prototype-instance observations such as exact wiring notes, ALSA routing tweaks, or validation outcomes can be recorded in [docs/pi-setup-log.md](/Users/markus/Workspace/jukebox/docs/pi-setup-log.md).

## Current Prototype Parts

- Raspberry Pi 3 Model B v1.2
- Fixed-mount QR scanner: Netum NT-91 in USB HID keyboard mode
- USB sound card for the V1 external-audio baseline: JSAUX ASDIOFJ2 USB Sound Card
- Amplifier for the current mono audio path: XY-AP50L
- Speaker for the current mono audio path: Pioneer TS-G1320F, wired to the amplifier's left speaker output

## Scanner Notes

- The software baseline expects the scanner to behave like a keyboard-style USB HID input device.
- The scanner should emit newline-terminated payloads so the jukebox can treat each completed line as one scan event.
- The Netum NT-91 provides a scan-receipt beep in hardware before playback confirmation arrives from the software stack.
- The NT-91 beep behavior can be adjusted with vendor configuration barcodes. See the Netum NT-91 support guide and its volume-configuration material: <https://support.netum.net/hc/en-us/articles/43770310381851-NT-91-Barcode-Scanner-Support-Guide>.
- Because the beep is scanner-local feedback, it should not be treated as proof that the jukebox runtime is fully ready or that playback has already succeeded.

## Audio Notes

- The current V1 baseline remains a USB sound card feeding the XY-AP50L amplifier and one Pioneer TS-G1320F speaker.
- `/etc/asound.conf` is part of that baseline because it selects the USB card for services and mixes stereo down to the single speaker on the amplifier's left output.
- EPIC 4 keeps volume control in the audio hardware path rather than adding built-in GPIO volume hardware.
- EPIC 4 volume preset cards are software-side Spotify Connect presets only; they do not replace the amplifier's own controls.
- Further enclosure integration, amplifier mounting, and acoustics remain separate future work.
