# Raspberry Pi Validation

This document defines the EPIC 3 validation stack: repeatable remote smoke checks plus manual hardware and recovery checks.
Use [`docs/pi-setup-log.md`](/Users/markus/Workspace/jukebox/docs/pi-setup-log.md) to record the current Pi's actual validation status and any bring-up-specific findings.

## Remote Smoke Validation

Use the smoke helper for repeatable remote checks:

```sh
JUKEBOX_PI_HOST=jukebox.local \
JUKEBOX_PI_RECEIVER_SERVICE_NAME=spotifyd.service \
JUKEBOX_SMOKE_URI='spotify:track:6rqhFgbbKwnb9MLmUQDhG6' \
./scripts/pi-smoke.sh
```

Expected remote checks:

- `spotifyd.service` is active
- `jukebox.service` is active
- recent `journalctl -u spotifyd.service` output is readable
- recent `journalctl -u jukebox.service` output is readable
- the receiver visibility snapshot reports `status_code: "ready"` before the system is treated as ready
- a one-shot stdin replay reaches `[PLAYBACK spotify] started ...` without an official Spotify client waking the receiver first

The visibility snapshot now distinguishes:

- `controller_auth_unavailable` with `spotify_api_auth_error`
- `network_unavailable` with `network_discovery_failed`
- `receiver_unavailable` with `device_not_listed`
- `ready` when the configured target is currently visible to Spotify

Interpret the remote snapshot carefully:

- If `spotifyd.service` is active but the snapshot reports `receiver_unavailable`, the receiver process is up but the Spotify Web API still does not see the configured target.
- If the snapshot reports `controller_auth_unavailable`, the Python app's refresh token or scopes are wrong even if the receiver process is healthy.
- If the snapshot reports `network_unavailable`, treat that as Wi-Fi, DNS, or Spotify-side reachability trouble until proven otherwise.
- If the replay fails with `connect_transfer_failed`, the target was visible but Spotify did not accept the transfer step cleanly.
- If the replay fails with `device_not_listed`, the receiver vanished between the visibility snapshot and the playback attempt.

If the smoke URI succeeds but the physical speaker stays silent, that is still a USB-audio path or hardware issue, not proof that the Spotify control path failed.

## Manual Scanner Validation

Remote replay is not enough for EPIC 3.
Run these manual checks on the physical prototype:

1. Confirm the mounted scanner reads a real laminated card.
2. Confirm the service logs a scan event from the `evdev` source.
3. Confirm the accepted scan triggers a playback-start event rather than only a dispatch attempt.
4. Confirm duplicate suppression still blocks an immediate repeated scan of the same card.
5. If you unplug and reconnect the scanner USB cable, confirm the service stays up and later returns to `ready`.

## Manual Audio Validation

The EPIC 3 baseline requires audible output through the Pi's USB sound card into an external powered speaker.

Check:

1. The speaker is connected to the USB sound card output.
2. `aplay -l` shows the USB sound card before you debug the jukebox app.
3. `speaker-test -c 2 -t wav` is audible on the speaker before deploying or debugging the jukebox app.
4. `aplay /usr/share/sounds/alsa/Front_Center.wav` is audible on the speaker as a simple sample playback check.
5. `/etc/asound.conf` exists when `spotifyd.service` needs the same USB ALSA default that worked interactively for the `pi` user.
6. Playback is audible after a successful scan or smoke replay.
7. If USB audio fails, any fallback to the Pi's analog output is recorded explicitly as troubleshooting, not as the baseline configuration.

If you temporarily fall back to the Pi's analog output, document why the USB path was unavailable.

## Repeated Clean Reboot Validation

A clean reboot must return the Pi to autonomous scan-to-playback readiness without ad hoc commands or another Spotify client waking the receiver:

```sh
JUKEBOX_PI_HOST=jukebox.local \
JUKEBOX_PI_RECEIVER_SERVICE_NAME=spotifyd.service \
JUKEBOX_SMOKE_URI='spotify:track:6rqhFgbbKwnb9MLmUQDhG6' \
JUKEBOX_SMOKE_REBOOT=1 \
JUKEBOX_SMOKE_REBOOT_COUNT=3 \
./scripts/pi-smoke.sh
```

For each reboot iteration:

1. `spotifyd.service` must be active.
2. `jukebox.service` must be active.
3. `journalctl -u jukebox.service -n 50 --no-pager` should show `[BOOT]` and then either a degraded dependency state or `[READY]`.
4. The receiver visibility snapshot must reach `status_code: "ready"` without opening an official Spotify client first.
5. The smoke replay must reach a playback-start event once the services are back.

If the reboot sequence has not been run yet on the current Pi, record that explicitly in the setup log rather than leaving the status implicit.

## Controlled Power-Cycle Validation

Run at least one controlled power-cycle validation:

1. Shut the system down cleanly if possible and remove power from the Pi and speaker.
2. Restore power.
3. Wait for Wi-Fi reconnect, `spotifyd.service`, and `jukebox.service`.
4. Run the remote smoke helper again without opening another Spotify client.
5. Record whether the runtime reached `ready`, a degraded state, or required intervention.

This test must be recorded manually even if the automated smoke checks already pass for clean reboots.

## Temporary Network Interruption Validation

Run at least one same-LAN network interruption test:

1. Start from a confirmed `ready` state.
2. Interrupt Wi-Fi or upstream network access briefly.
3. Confirm the jukebox runtime stays up and surfaces `network_unavailable` or `receiver_unavailable` instead of silently hanging.
4. Restore the network.
5. Confirm the runtime returns to `ready` without restarting the service manually.
6. Run a fresh physical scan or smoke replay after recovery.

Record whether recovery was automatic, delayed, or failed.

## Safe Troubleshooting Checks

Use this order when the assembled device is not behaving correctly:

1. Check `systemctl is-active spotifyd.service`.
2. Check `systemctl is-active jukebox.service`.
3. Read the last 50 lines of both journals.
4. Run `./scripts/pi-smoke.sh` and note the reported `status_code` and `reason_code`.
5. Only move on to scanner or audio troubleshooting after the receiver visibility snapshot makes the controller-auth, network, and receiver state clear.

## Build Readiness Notes

Review these runtime-sensitive notes before enclosure work starts:

- The scanner mount must preserve the same `/dev/input/by-id/...-event-kbd` path after final cable routing.
- The scanner USB cable and the USB sound card cable both need strain relief and a service path that does not require destructive disassembly.
- The rear or underside of the enclosure must still allow access to power, the speaker cable, and the service panel for SSH or SD-card recovery work.
- The Pi power lead and external speaker power lead must be reachable without removing the scanner or opening the main body.
- The enclosure should leave enough service access to unplug and reconnect the scanner and USB sound card during validation.
