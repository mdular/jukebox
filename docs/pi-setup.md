# Raspberry Pi Setup

This is the authoritative EPIC 2 bring-up guide for a fresh Raspberry Pi 3 running Raspberry Pi OS Lite.
It replaces the earlier notes in `spec/pisetup.md`.

## Scope

This guide covers:

- flashing Raspberry Pi OS Lite
- headless Wi-Fi and SSH access
- baseline packages for the jukebox service
- `raspotify` as the supported Spotify Connect receiver
- stable scanner binding through `/dev/input/by-id/...-event-kbd`
- the tracked environment-file shape under `/etc/jukebox/jukebox.env`

This guide does not automate SD card imaging or physical speaker/scanner installation.

## 1. Flash Raspberry Pi OS Lite

Use Raspberry Pi Imager and select Raspberry Pi OS Lite for Raspberry Pi 3.
Before writing the image, open the advanced options and set:

- hostname
- a user account
- Wi-Fi SSID, password, and country
- SSH enabled
- the correct timezone

The earlier `spec/pisetup.md` notes remain a useful summary for the headless imaging flow, but this document is now the maintained version.

## 2. First Boot and Base Access

Boot the Pi, wait for it to join Wi-Fi, and connect over SSH:

```sh
ssh pi@jukebox.local
```

If mDNS is unavailable on your network, use the Pi's DHCP-assigned IP address instead.

## 2a. Optional: Configure SSH Key Authentication

If you will be running repeated `ssh`, `scp`, or Pi helper script commands from your development machine, set up SSH key-based auth once so the Pi account password prompts stop.

Generate a dedicated key locally if you do not already have one you want to reuse:

```sh
ssh-keygen -t ed25519 -f ~/.ssh/jukebox_pi -C "jukebox-pi"
```

Install the public key on the Pi.
If `ssh-copy-id` is available on your machine:

```sh
ssh-copy-id -i ~/.ssh/jukebox_pi.pub pi@jukebox.local
```

If `ssh-copy-id` is not available, append the key manually:

```sh
cat ~/.ssh/jukebox_pi.pub | ssh pi@jukebox.local "umask 077; mkdir -p ~/.ssh; touch ~/.ssh/authorized_keys; cat >> ~/.ssh/authorized_keys; chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys"
```

To make the key apply automatically for this host, add a matching host entry to your local `~/.ssh/config`:

```sshconfig
Host jukebox.local
  IdentityFile ~/.ssh/jukebox_pi
  IdentitiesOnly yes
  AddKeysToAgent yes
```

If your local SSH agent is not already loading that key, add it once:

```sh
ssh-add ~/.ssh/jukebox_pi
```

Then verify that passwordless login works:

```sh
ssh pi@jukebox.local 'hostname'
```

After this, the same key-based auth should also be used by `scp` and by the repo's Pi helper scripts because they already call the normal local `ssh`/`scp` clients.

## 3. Install Baseline Packages

Update the Pi and install the runtime prerequisites:

```sh
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y python3-venv python3-pip python3-dev build-essential libevdev-dev alsa-utils
```

`alsa-utils` is included so you can verify the USB sound card output before you deploy the jukebox service.

## 4. Install `raspotify`

EPIC 2 supports `raspotify` as the receiver path.
Install it using the current official `raspotify` instructions for Raspberry Pi OS, then confirm the service exists:

https://dtcooper.github.io/raspotify/

```sh
systemctl status raspotify.service
```

Choose the Spotify Connect receiver name you want `raspotify` to advertise on the Pi, for example `jukebox`.
This is separate from `JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME`: `raspotify` has its own config, and our app has its own env file.
On current installs this is usually configured in `/etc/raspotify/conf`; some older packages use `/etc/default/raspotify`.

Edit the `raspotify` config on the Pi, set its own advertised device name to `jukebox`, and restart `raspotify`:

```sh
sudoedit /etc/raspotify/conf
sudo systemctl restart raspotify.service
sudo systemctl status raspotify.service
```

Then separately put that same exact string into `/etc/jukebox/jukebox.env`:

```dotenv
JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME=jukebox
```

## 5. Run the Bootstrap Helper

Run the repo bootstrap helper from your development machine only after `raspotify.service` exists:

```sh
JUKEBOX_PI_HOST=jukebox.local ./scripts/pi-bootstrap.sh
```

That script prepares `/opt/jukebox`, ensures `/etc/jukebox` exists, and copies the tracked env template into place if the real env file does not exist yet.

## 6. Configure and Verify USB Audio Output

The EPIC 2 baseline audio path is a USB sound card feeding an external powered speaker.
After plugging in the USB card and running `sudo raspi-config` to select USB audio, verify the audio path before deploying the jukebox service:

```sh
aplay -l
speaker-test -c 2 -t wav
aplay /usr/share/sounds/alsa/Front_Center.wav
```

`aplay -l` should show the USB sound card.
Use `speaker-test` to confirm that the default output reaches the external speaker, then use the `aplay` sample as a simple spoken confirmation.
If these commands do not produce sound, fix the Pi-side USB audio routing first and rerun the same checks before proceeding.

One important detail from bring-up: a per-user `/home/pi/.asoundrc` may make manual tests work for the `pi` user while `raspotify.service` still stays silent.
To make the USB card the system-wide ALSA default for services as well, copy the working config into `/etc/asound.conf`:

```sh
sudo cp /home/pi/.asoundrc /etc/asound.conf
sudo systemctl restart raspotify.service
```

Then test Spotify playback again through `raspotify`.
Use `/etc/asound.conf` as the authoritative fix for service playback, not only `~/.asoundrc`.

Keep the Pi's 3.5 mm analog output only as a fallback troubleshooting path if the USB card is missing or fails.

## 7. Discover the Scanner Device Path

Plug in the USB scanner and identify the stable keyboard event path:

```sh
ls -l /dev/input/by-id
```

Look for the scanner entry ending in `-event-kbd`.
Store that exact path in `/etc/jukebox/jukebox.env` as `JUKEBOX_SCANNER_DEVICE`.

The EPIC 2 runtime expects the scanner to emit newline-terminated Spotify URI payloads.

## 8. Configure `/etc/jukebox/jukebox.env`

Start from the tracked template:

```sh
sudo cp /opt/jukebox/systemd/jukebox.env.example /etc/jukebox/jukebox.env
sudo chmod 640 /etc/jukebox/jukebox.env
```

Fill in:

- Spotify client credentials
- Spotify refresh token
- `JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME`
- `JUKEBOX_SCANNER_DEVICE`

Recommended EPIC 2 values:

```dotenv
JUKEBOX_INPUT_BACKEND=evdev
JUKEBOX_PLAYBACK_BACKEND=spotify
JUKEBOX_LOG_FORMAT=json
JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS=5.0
JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS=0.25
```

Keep secrets out of the repository and out of committed files.

## 9. Deploy and Enable the Service

Use the deploy helper from your development machine:

```sh
JUKEBOX_PI_HOST=jukebox.local ./scripts/pi-deploy.sh
```

The deploy script installs the package into `/opt/jukebox/.venv`, refreshes the `systemd` unit, and restarts `jukebox.service`.

## 10. Confirm Boot-to-Ready State

After deployment, verify:

```sh
ssh pi@jukebox.local 'systemctl is-active raspotify.service'
ssh pi@jukebox.local 'systemctl is-active jukebox.service'
ssh pi@jukebox.local 'journalctl -u jukebox.service -n 50 --no-pager'
```

When startup is healthy, the service output should include the boot and ready states and no receiver/scanner startup failure event.
