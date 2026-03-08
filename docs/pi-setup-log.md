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

## Current Validation Status

Confirmed working on this Pi:

- `raspotify` is visible as `jukebox` in Spotify Connect
- USB audio playback works through the external speaker after the `/etc/asound.conf` fix
- the physical QR scanner is readable through the configured `evdev` path
- end-to-end card scanning now works after fixing shifted `:` and uppercase handling in the `evdev` adapter

Not yet completed or not yet reliable on this Pi:

- clean reboot validation after deployment
