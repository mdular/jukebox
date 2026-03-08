# Raspberry Pi Validation

This document defines the EPIC 2 validation stack: automated remote smoke checks plus manual hardware checks.
Use [`docs/pi-setup-log.md`](/Users/markus/Workspace/jukebox/docs/pi-setup-log.md) to record the current prototype's actual validation status and any bring-up-specific findings.

## Remote Smoke Validation

Use the smoke helper for repeatable remote checks:

```sh
JUKEBOX_PI_HOST=jukebox.local \
JUKEBOX_SMOKE_URI='spotify:track:6rqhFgbbKwnb9MLmUQDhG6' \
./scripts/pi-smoke.sh
```

Expected remote checks:

- `raspotify.service` is active
- `jukebox.service` is active
- recent `journalctl -u raspotify.service` output is readable
- recent `journalctl -u jukebox.service` output is readable
- the current Spotify Web API `/me/player/devices` snapshot is readable
- a one-shot stdin replay confirms playback start on the configured target device

If the smoke URI succeeds but the physical speaker stays silent, that is a USB-audio path or hardware issue, not a proof that the Spotify control path failed.

Interpret the remote device snapshot carefully:

- If `raspotify.service` is active but `target_visible` is `false`, the receiver process is up but the Spotify Web API still does not see the configured target device.
- If the device list is empty until an official Spotify client is opened, that points to a receiver-registration or discovery problem rather than a scanner problem.
- If `target_visible` becomes `true` only after manually connecting to `jukebox` from a phone or desktop app, record that explicitly before changing the app code. That distinction matters because it separates a boot-time race from a deeper receiver-visibility problem.

## Manual Scanner Validation

Remote replay is not enough for EPIC 2.
Run these manual checks on the physical prototype:

1. Confirm the mounted scanner reads a real laminated card.
2. Confirm the service logs a scan event from the `evdev` source.
3. Confirm the accepted scan triggers a playback-start event rather than only a dispatch attempt.
4. Confirm duplicate suppression still blocks an immediate repeated scan of the same card.

## Manual Audio Validation

The EPIC 2 baseline requires audible output through the Pi's USB sound card into an external powered speaker.

Check:

1. The speaker is connected to the USB sound card output.
2. `aplay -l` shows the USB sound card before you debug the jukebox app.
3. `speaker-test -c 2 -t wav` is audible on the speaker before deploying or debugging the jukebox app.
4. `aplay /usr/share/sounds/alsa/Front_Center.wav` is audible on the speaker as a simple sample playback check.
5. `/etc/asound.conf` exists when `raspotify.service` needs the same USB ALSA default that worked interactively for the `pi` user.
6. Playback is audible after a successful scan or smoke replay.
7. If USB audio fails, any fallback to the Pi's analog output is recorded explicitly as troubleshooting, not as the baseline configuration.

If you temporarily fall back to the Pi's analog output, document why the USB path was unavailable.

## Clean Reboot Validation

A clean reboot must return the Pi to scan-ready state without ad hoc commands:

```sh
JUKEBOX_PI_HOST=jukebox.local \
JUKEBOX_SMOKE_URI='spotify:track:6rqhFgbbKwnb9MLmUQDhG6' \
JUKEBOX_SMOKE_REBOOT=1 \
./scripts/pi-smoke.sh
```

After reboot:

1. `raspotify.service` must be active.
2. `jukebox.service` must be active.
3. `journalctl -u raspotify.service -n 50 --no-pager` should not show an obvious receiver startup failure.
4. The Spotify Web API device snapshot should show whether `jukebox` is visible without opening another Spotify client first.
5. The jukebox journal should show the boot and ready states without startup probe failures.
6. A fresh physical card scan should still trigger playback.

If the reboot test has not been run yet on the current prototype, record that explicitly in the setup log rather than leaving the status implicit.
