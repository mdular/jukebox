# Raspberry Pi Setup Log

This file records the concrete bring-up values used for the current EPIC 2 Raspberry Pi setup.
It is intentionally instance-specific.
Secrets are not stored here.

Date: 2026-03-08

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

## Completed Setup Steps

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

## Current Validation Status

Confirmed working on this Pi:

- `raspotify` is visible as `jukebox` in Spotify Connect
- USB audio playback works through the external speaker after the `/etc/asound.conf` fix
- the physical QR scanner is readable through the configured `evdev` path
- end-to-end card scanning now works after fixing shifted `:` and uppercase handling in the `evdev` adapter
- clean reboot validation now returns the jukebox service to a stable ready state without a restart loop
- cardboard-prototype handling has been validated with successful real card scans during family testing

Not yet completed or not yet reliable on this Pi:

- immediate post-boot receiver visibility in Spotify's Web API
- playback still depends on the receiver becoming visible to Spotify after manual activation
- autonomous receiver activation after reboot without using another Spotify client
