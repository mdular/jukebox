# QR Card Jukebox - Concept Specification

## Overview
A screenless, child-friendly jukebox that plays music when laminated cards with QR codes are placed in a scanning bay.
Each card contains a Spotify URI. The system scans the code and immediately starts playback.

The device is designed as a wooden cube with a recessed front scan bay and a top tray for storing cards.

The system is designed to be built in stages:
- V1: Validate the interaction and playback using external speakers
- V2: Add internal stereo speakers and refined controls

---

# Goals

Primary goals:
- Extremely simple interaction for young children
- Fast addition of new music (print a new QR card)
- Robust hardware with minimal maintenance
- No screens
- Automatic startup and recovery after power loss

Secondary goals:
- Clean physical design resembling a toy appliance
- Modular hardware so components can evolve
- Ability to fall back to local audio playback in the future

---

# Target Users

Primary:
- Children aged 4–7

Secondary:
- Older children as the system evolves

Key UX principles:
- Physical cards create tangible interaction
- No menus or complex controls
- Immediate response when a card is inserted

---

# System Architecture

## High-Level Flow

Card inserted → QR scanned → URI parsed → Spotify playback triggered → Music plays

Components:

QR Scanner (USB HID)
↓
Raspberry Pi 3
↓
Playback Controller Service
↓
Spotify Connect Playback
↓
Audio Output

---

# Hardware Specification

## Compute
Raspberry Pi 3 Model B v1.2

Requirements:
- WiFi connectivity
- 4 USB ports
- Headless operation
- MicroSD storage

---

## Scanner

Type:
Fixed mount QR presentation scanner

Interface:
USB HID keyboard mode

Behavior:
- Automatically scans when QR enters detection field
- Emits decoded string followed by newline

Mounting:
- Positioned behind recessed lip
- Tilted downward 20–35 degrees
- Protected from direct contact by enclosure geometry

---

## Enclosure

Form factor:
Wooden cube

Material:
12 mm plywood

Dimensions:
Target range: 18–22 cm cube

External features:

Front
- Recessed scan bay
- LED indicator inside bay

Top
- Card storage tray

Rear
- Power input
- Temporary audio cable exit
- Service panel

Sides
- Reserved for future speaker installation (V2)

---

## Scan Bay Geometry

Opening:
10–12 cm wide
6–7 cm tall

Depth:
4–6 cm

Features:
- Card ramp angle: 10–15 degrees
- Physical stop lip
- Scanner tilt: 20–35 degrees downward

Goal:
Ensure consistent QR positioning and minimize glare.

---

# Audio System

## V1 Audio

Temporary output:
USB sound card connected to the Raspberry Pi

External powered speaker connected via cable exiting rear panel.

Optional upgrade:
Use the Pi's 3.5 mm analog output only as a fallback troubleshooting path if the USB card is unavailable.

---

## V2 Audio (Planned)

Internal stereo system.

Configuration:
2x full-range speakers (left and right side panels)

Amplifier:
5V Class D stereo amplifier

Controls:
Panel-mounted rotary encoder for volume

Speaker target specs:
- Diameter: ~3 inch (≈8 cm)
- Impedance: 4 ohm
- Power: 3–5W

Internal structure:
Separate speaker chamber from electronics.

---

# Controls and Indicators

## V1

Status LED
- Located in scan bay
- Provides feedback

Optional STOP button

Volume handled externally via speaker.

---

## V2

Controls:

Volume knob
Rotary encoder connected to GPIO

STOP button

Optional:
Next track button

---

# Card Design

Cards:
Laminated printed cards

Size:
Approximately credit-card sized

QR placement:
Consistent location on each card

Recommended size:
25–35 mm square

Content format:
Spotify URI

Examples:

spotify:track:ID
spotify:album:ID
spotify:playlist:ID

---

# Software Architecture

## Operating System

Raspberry Pi OS Lite

Headless operation via SSH during setup.

---

## Playback Engine

Spotify Connect receiver running on device.

Options:
raspotify
or
spotifyd

Device appears as a Spotify Connect speaker.

Requires Spotify Premium account.

---

## Controller Service

Local daemon responsible for:

- Reading scanner input
- Parsing scanned URIs
- Triggering playback
- Managing LED feedback
- Handling optional buttons

Service name:
jukeboxd

Runs via systemd.

---

## Scanner Input

Scanner behaves like USB keyboard.

Typical input example:

spotify:track:6rqhFgbbKwnb9MLmUQDhG6

Terminated by newline.

Controller reads from stdin device.

---

# Playback Logic

State machine:

IDLE
↓
SCAN DETECTED
↓
VALID URI
↓
TRIGGER PLAYBACK
↓
PLAYING

Duplicate scans within short window ignored.

Default behavior:
Latest scan replaces current playback.

---

# Feedback States

LED behavior:

Idle
Dim steady light

Scan detected
Quick pulse

Playback started
Short bright glow

Error
Blink pattern

---

# Reliability Requirements

Device must:

- Boot automatically after power loss
- Reconnect WiFi automatically
- Start Spotify receiver
- Start controller service
- Become usable without manual intervention

---

# Card Content Workflow

Add a new song:

1. Copy Spotify URI
2. Generate QR code
3. Print card
4. Laminate card
5. Place card in tray

Time required: ~2 minutes.

---

# Future Extensions

Local playback fallback
Mapping file linking Spotify URIs to local media.

Example mapping:

spotify:track:XYZ → /media/music/song.mp3

Additional features:

Queue mode
Story cards
Podcast cards
Child-created playlists

---

# Version Roadmap

## V1

QR scanning
Spotify playback
External speakers
Status LED
Basic enclosure

Goal:
Validate interaction with children.

---

## V2

Internal stereo speakers
Volume knob
Improved acoustics
Additional controls

Goal:
Polished standalone device.

---

# Non-Goals

For now the system intentionally excludes:

Screens
Touch interfaces
Mobile apps
Complex configuration UI

Focus remains on physical interaction.

---

# End of Specification
