# Raspberry Pi Setup Log

This file records the concrete bring-up values and prototype findings used to move from the EPIC 2 Pi setup to the EPIC 3 hardening baseline.
It is intentionally instance-specific.
Secrets are not stored here.

Date: 2026-03-08

## EPIC 3 Note

The receiver findings below were recorded against the earlier `raspotify` prototype path.
They are kept because they explain why EPIC 3 moved the supported receiver baseline to `spotifyd`.
Repeated reboot, power-cycle, and network-recovery validation must be rerun on the `spotifyd` path before EPIC 3 can be considered fully validated on this Pi.

## `spotifyd` Transition Note

Observed on 2026-03-09 while moving this Pi from the historical `raspotify` prototype path to the EPIC 3 `spotifyd` baseline:

- `raspotify.service` was still installed and running even after `spotifyd.service` had been built and enabled.
- Leaving both receiver services active at the same time is not a valid EPIC 3 baseline because it can confuse Spotify Connect discovery and audio ownership on the Pi.
- `raspotify.service` therefore had to be disabled and masked before validating `spotifyd.service`.

Applied commands:

```sh
sudo systemctl disable --now raspotify.service
sudo systemctl mask raspotify.service
```

Follow-up expectation:

- future EPIC 3 validation on this Pi should assume `spotifyd.service` is the only active Spotify receiver service
- `docs/pi-setup.md` should stay receiver-clean and continue to assume `raspotify` is not part of the supported path
- if we ever want to use `raspotify` again for prototyping or testing, we can unmask and re-enable it, but that should be a conscious choice rather than an accidental leftover.

## Hardware Seen On This Pi

Scanner device path:

```text
/dev/input/by-id/usb-BF_SCAN_SCAN_KEYBOARD_A-00000-event-kbd
```

USB audio card input event path observed from `ls -l /dev/input/by-id`:

```text
/dev/input/by-id/usb-GHW-136D-20231007_USB_Audio_20210726905926-event-if03
```

Notes:

- The scanner path above is the value to use for `JUKEBOX_SCANNER_DEVICE`.
- The USB audio `event-if03` path is not the scanner path and should not be used for `JUKEBOX_SCANNER_DEVICE`.
- USB audio is now the default V1 audio path on this Pi.

## Historical EPIC 2 Setup Steps

1. Installed and enabled `raspotify` on the Raspberry Pi.
2. Plugged in the USB sound card.
3. Ran `sudo raspi-config`.
4. Changed the audio output to USB audio.
5. Verified `/dev/input/by-id` and identified the scanner device path.
6. Confirmed that `/home/pi/.asoundrc` pointed to USB audio card `1`.
7. Copied `/home/pi/.asoundrc` to `/etc/asound.conf` so `raspotify.service` would use the same USB ALSA default.
8. Restarted `raspotify.service` and confirmed Spotify playback became audible.

## Current Runtime Values To Use

For `/etc/jukebox/jukebox.env`:

```dotenv
JUKEBOX_INPUT_BACKEND=evdev
JUKEBOX_SCANNER_DEVICE=/dev/input/by-id/usb-BF_SCAN_SCAN_KEYBOARD_A-00000-event-kbd
JUKEBOX_PLAYBACK_BACKEND=spotify
```

Still required separately:

- `JUKEBOX_SPOTIFY_CLIENT_ID`
- `JUKEBOX_SPOTIFY_CLIENT_SECRET`
- `JUKEBOX_SPOTIFY_REFRESH_TOKEN`
- `JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME`

## Device Discovery Snapshot

Observed command output:

```text
ls -l /dev/input/by-id
total 0
lrwxrwxrwx 1 root root 9 Mar  8 11:10 usb-BF_SCAN_SCAN_KEYBOARD_A-00000-event-kbd -> ../event3
lrwxrwxrwx 1 root root 9 Mar  8 09:54 usb-GHW-136D-20231007_USB_Audio_20210726905926-event-if03 -> ../event0
```

Interpretation:

- `usb-BF_SCAN_SCAN_KEYBOARD_A-00000-event-kbd` is the QR scanner.
- `usb-GHW-136D-20231007_USB_Audio_20210726905926-event-if03` belongs to the USB audio device.

## ALSA Fix Applied

Observed state before the fix:

- `aplay -l` showed the USB sound card as `card 1`
- `/home/pi/.asoundrc` existed and pointed playback to `card 1`
- `/etc/asound.conf` did not exist
- manual audio tests worked for user `pi`, but `raspotify` playback stayed silent

Applied fix:

```sh
sudo cp /home/pi/.asoundrc /etc/asound.conf
sudo systemctl restart raspotify.service
```

Result:

- `raspotify` started sending audio to the USB sound card correctly
- Spotify playback became audible through the external speaker

## Clean Reboot Validation

Validated on 2026-03-08.

Observed after reboot:

- `raspotify.service` reached `active`
- `jukebox.service` reached `active`
- the jukebox journal showed `[BOOT]` followed by `[READY] waiting for scan input`
- the service no longer entered a restart loop when Spotify's device list was empty
- the Spotify Web API `/me/player/devices` snapshot still returned `device_count: 0` immediately after boot
- the cached Spotify device ID stayed the same across reboot, so this was not a changing-device-id problem
- direct-target playback attempts and transfer-playback retries against that stable device ID still failed with HTTP `404`

Observed after manual activation from the phone:

- `raspotify` connected to Spotify's access point and authenticated only after the phone selected the receiver
- `jukebox` appeared in `/me/player/devices`
- Spotify reported `jukebox` as an active `Speaker`
- playback from the jukebox app started working reliably again

Interpretation:

- reboot-to-ready behavior is now validated for the jukebox service itself
- immediate post-boot receiver visibility through Spotify's Web API is still not reliable on this Pi
- manual activation from a Spotify client is still required before the receiver becomes visible to the Web API
- the remaining reboot gap is receiver activation on the Spotify/`raspotify` side, not scanner input handling inside the jukebox app
- stable reboot into autonomous playback should be treated as EPIC 3 hardening work

## `spotifyd` Reboot Validation

Validated on 2026-03-09 after reboot, with `raspotify.service` disabled and masked.

Observed after reboot:

- `spotifyd.service` reached `active`
- `jukebox.service` reached `active`
- the `spotifyd` journal showed OAuth login, zeroconf advertising, AP connection, and successful Spotify authentication
- the jukebox journal showed `[BOOT]`, then `receiver_unavailable` with `device_not_listed`, then recovery to `[READY]` about five seconds later
- the receiver visibility snapshot reported `status_code: "ready"` and showed the configured `jukebox` target as a visible Spotify `Speaker`
- a one-shot stdin replay using `spotify:track:6rqhFgbbKwnb9MLmUQDhG6` succeeded with `[PLAYBACK spotify] started track on jukebox`
- the track was also audible through the connected external speaker during that replay

Interpretation:

- on this Pi, the `spotifyd` baseline now survives reboot and becomes visible to Spotify without relying on the old `raspotify` path
- the short degraded window before `ready` is consistent with the EPIC 3 readiness contract because the runtime stayed observable and only emitted `ready` after the receiver was actually visible
- this is the first confirmed reboot-to-visible-playback success on the supported EPIC 3 receiver path
- the result was not only API-visible playback state; it also produced audible output on the speaker path

## `spotifyd` Repeated Reboot Validation

Validated on 2026-03-09 with the repeated reboot smoke flow from [docs/pi-validation.md](/Users/markus/Workspace/jukebox/docs/pi-validation.md).

Observed during repeated reboot validation:

- the repeated reboot smoke sequence completed successfully on the `spotifyd` baseline
- the receiver became visible again after each reboot without opening an official Spotify client first
- the smoke replay remained audible through the external speaker after reboot

Interpretation:

- repeated clean reboot recovery is now confirmed on this Pi for the supported `spotifyd` path

## `spotifyd` Controlled Power-Cycle Validation

Validated on 2026-03-09 after fully removing and restoring power to the Pi and speaker.

Observed after power-cycle:

- `spotifyd.service` recovered without manual intervention
- `jukebox.service` recovered without manual intervention
- the receiver became visible to Spotify again without another Spotify client waking it
- the smoke validation succeeded again on the restored system

Interpretation:

- the supported `spotifyd` baseline now survives a controlled power-cycle on this Pi
- EPIC 3 validation on this Pi no longer depends only on clean reboot behavior

## `spotifyd` Network Interruption Validation

Validated on 2026-03-09 by disabling upstream internet access at the router while playback was already in progress, then restoring connectivity later.

Observed during the interruption:

- an already-playing track continued for a while after internet access was removed, then eventually stopped
- the jukebox runtime emitted `[NETWORK] unavailable: network_discovery_failed`
- structured logs recorded `network_unavailable` with `reason_code: "network_discovery_failed"` and the Spotify transport error `Connection refused`
- real `evdev` card scans were still received and accepted during the outage
- playback dispatch for new scans failed cleanly with `network_discovery_failed`

Observed after connectivity returned:

- the runtime recovered to `[READY]` without restarting either service manually
- a fresh real card scan later succeeded and started playback again on the configured `jukebox` target

Interpretation:

- temporary upstream network loss now produces the expected EPIC 3 degraded state instead of a silent hang
- scan intake remains functional during the degraded state even though new playback dispatch fails
- the supported `spotifyd` baseline recovered automatically once internet connectivity returned
- this validation also confirms real post-boot `evdev` scanner-card playback on the `spotifyd` baseline, not only stdin smoke replay

## Current Validation Status

Confirmed working on this Pi:

- USB audio playback works through the external speaker after the `/etc/asound.conf` fix
- the physical QR scanner is readable through the configured `evdev` path
- end-to-end card scanning now works after fixing shifted `:` and uppercase handling in the `evdev` adapter
- clean reboot validation now returns the jukebox service to a stable ready state without a restart loop
- cardboard-prototype handling has been validated with successful real card scans during family testing
- the EPIC 3 runtime now exposes degraded dependency states instead of treating scanner or receiver readiness as startup-only
- `spotifyd.service` is now running as the supported EPIC 3 receiver baseline on this Pi
- after reboot on 2026-03-09, the `spotifyd` receiver became visible to Spotify and accepted a successful stdin-triggered playback dispatch
- that 2026-03-09 stdin-triggered playback was audible through the connected external speaker
- repeated clean reboot validation now succeeds on the `spotifyd` baseline on this Pi
- a controlled power-cycle validation now succeeds on the `spotifyd` baseline on this Pi
- temporary network interruption now surfaces `network_unavailable`, recovers back to `ready`, and accepts playback again once connectivity returns
- real post-boot scanner-card playback is confirmed on the `spotifyd` baseline through the physical `evdev` path
- real scans during the network outage were still accepted and failed cleanly with `network_discovery_failed`

Not yet completed or not yet reliable on this Pi:
- no additional EPIC 3 validation gaps are currently recorded on this Pi
