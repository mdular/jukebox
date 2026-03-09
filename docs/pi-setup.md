# Raspberry Pi Setup

This is the authoritative EPIC 3 bring-up guide for a fresh Raspberry Pi 3 running Raspberry Pi OS Lite.
It replaces the earlier EPIC 2 receiver guidance.

## Scope

This guide covers:

- flashing Raspberry Pi OS Lite
- headless Wi-Fi and SSH access
- baseline packages for the jukebox service
- `spotifyd` as the supported Spotify Connect receiver baseline
- stable scanner binding through `/dev/input/by-id/...-event-kbd`
- the tracked environment-file shape under `/etc/jukebox/jukebox.env`
- the separation between controller-side Spotify Web API credentials and receiver-side session material

This guide does not automate SD card imaging or physical speaker/scanner installation.

## 1. Flash Raspberry Pi OS Lite

Use Raspberry Pi Imager and select Raspberry Pi OS Lite for Raspberry Pi 3.
Before writing the image, open the advanced options and set:

- hostname
- a user account
- Wi-Fi SSID, password, and country
- SSH enabled
- the correct timezone

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

## 3. Install Baseline Packages

Update the Pi and install the runtime prerequisites:

```sh
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y python3-venv python3-pip python3-dev build-essential libevdev-dev alsa-utils
```

`alsa-utils` is included so you can verify the USB sound card output before you deploy the jukebox service.

## 4. Install and Configure `spotifyd`

EPIC 3 is outcome-driven and treats `spotifyd` as the supported receiver baseline because the recorded EPIC 2 `raspotify` path on this Pi still required manual receiver activation after reboot.

The upstream `spotifyd` docs say some Linux distributions package it, but Raspberry Pi OS may not.
If `sudo apt-get install -y spotifyd` fails with `Unable to locate package`, install the upstream release binary instead.
As of 2026-03-09, the current upstream release used in this guide is `v0.4.2`.
If that latest prebuilt binary still links against `libssl.so.1.1` on your Pi OS image, treat it as a distro-compatibility issue and use the source-build fallback below rather than hunting for an older OpenSSL package.

First, check the Pi architecture:

```sh
uname -m
```

Use the upstream release that matches the result:

- `armv7l` or `armhf` on a 32-bit Pi 3 install: use the `spotifyd-linux-armv7-default.tar.gz` asset
- `aarch64` on a 64-bit Pi install: use the `spotifyd-linux-aarch64-default.tar.gz` asset

Example for a Raspberry Pi 3 running 32-bit Raspberry Pi OS, using the current upstream release `v0.4.2`:

```sh
SPOTIFYD_VERSION=v0.4.2
cd /tmp
curl -L -o spotifyd.tar.gz \
  "https://github.com/Spotifyd/spotifyd/releases/download/${SPOTIFYD_VERSION}/spotifyd-linux-armv7-default.tar.gz"
tar -xzf spotifyd.tar.gz
cd spotifyd-*/
chmod +x spotifyd
sudo chown root:root spotifyd
sudo mv spotifyd /usr/local/bin/spotifyd
curl -L -o /tmp/spotifyd.service \
  "https://raw.githubusercontent.com/Spotifyd/spotifyd/${SPOTIFYD_VERSION}/contrib/spotifyd.service"
sed 's#/usr/bin/spotifyd#/usr/local/bin/spotifyd#' /tmp/spotifyd.service >/tmp/spotifyd.service.local
sudo install -m 644 /tmp/spotifyd.service.local /etc/systemd/system/spotifyd.service
sudo systemctl daemon-reload
systemctl status spotifyd.service
```

Example for a Raspberry Pi running 64-bit Raspberry Pi OS (`uname -m` returns `aarch64`):

```sh
SPOTIFYD_VERSION=v0.4.2
cd /tmp
curl -L -o spotifyd.tar.gz \
  "https://github.com/Spotifyd/spotifyd/releases/download/${SPOTIFYD_VERSION}/spotifyd-linux-aarch64-default.tar.gz"
tar -xzf spotifyd.tar.gz
cd spotifyd-*/
chmod +x spotifyd
sudo chown root:root spotifyd
sudo mv spotifyd /usr/local/bin/spotifyd
curl -L -o /tmp/spotifyd.service \
  "https://raw.githubusercontent.com/Spotifyd/spotifyd/${SPOTIFYD_VERSION}/contrib/spotifyd.service"
sed 's#/usr/bin/spotifyd#/usr/local/bin/spotifyd#' /tmp/spotifyd.service >/tmp/spotifyd.service.local
sudo install -m 644 /tmp/spotifyd.service.local /etc/systemd/system/spotifyd.service
sudo systemctl daemon-reload
systemctl status spotifyd.service
```

If `spotifyd.service` exits with `status=127` on the Pi, verify that you installed the release asset matching `uname -m`.
If `ldd /usr/local/bin/spotifyd` shows missing `libssl.so.1.1` or `libcrypto.so.1.1`, the downloaded binary is not compatible with the OpenSSL version on that Pi OS image.
In that case, stop using the prebuilt binary and build `spotifyd` from source on the Pi against the Pi's current system libraries.

Source-build fallback on Raspberry Pi OS:

```sh
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  pkg-config \
  curl \
  libasound2-dev \
  libssl-dev \
  libclang-dev \
  cmake

curl https://sh.rustup.rs -sSf | sh -s -- -y
. "$HOME/.cargo/env"

mkdir -p "$HOME/.cache/spotifyd-build/tmp" "$HOME/.cache/spotifyd-build/target"
export TMPDIR="$HOME/.cache/spotifyd-build/tmp"
export CARGO_TARGET_DIR="$HOME/.cache/spotifyd-build/target"
export CARGO_BUILD_JOBS=1
export CARGO_PROFILE_RELEASE_LTO=false

cargo install spotifyd --locked --no-default-features --features alsa_backend
sudo install -m 755 "$HOME/.cargo/bin/spotifyd" /usr/local/bin/spotifyd

curl -L -o /tmp/spotifyd.service \
  "https://raw.githubusercontent.com/Spotifyd/spotifyd/v0.4.2/contrib/spotifyd.service"
sed 's#/usr/bin/spotifyd#/usr/local/bin/spotifyd#' /tmp/spotifyd.service >/tmp/spotifyd.service.local
sudo install -m 644 /tmp/spotifyd.service.local /etc/systemd/system/spotifyd.service
sudo systemctl daemon-reload
sudo systemctl restart spotifyd.service
sudo systemctl status spotifyd.service
```

On Raspberry Pi OS Lite, `/tmp` is often mounted as RAM-backed `tmpfs`.
If you run `cargo install spotifyd --locked` without overriding `TMPDIR`, the Rust build may fill `/tmp` and fail with `No space left on device` even when `/` still has plenty of free space.
The `TMPDIR` and `CARGO_TARGET_DIR` exports above move temporary files and compiled artifacts onto the persistent filesystem under the `pi` user's home directory instead.
On a Raspberry Pi 3, the optimized default `spotifyd` build can also be killed by the kernel OOM killer during the final compile or link step.
The guide's baseline config uses `backend = "alsa"` and `use_mpris = false`, so the source-build fallback now compiles only the `alsa_backend` feature, forces a single build job, and disables release LTO to reduce peak memory use.
Expect this source-build fallback to be slow on a Raspberry Pi 3.
With the low-memory settings above, a successful `cargo install` can still take about 60 to 90 minutes.

If you prefer not to pin a release manually, use the latest release listed by the upstream project and substitute the tag in the two URLs above.

Optional cleanup after a successful source build:

```sh
rm -rf ~/.cache/spotifyd-build
rm -f ~/.cargo/bin/spotifyd
```

Those two paths are only build artifacts after `sudo install -m 755 "$HOME/.cargo/bin/spotifyd" /usr/local/bin/spotifyd` succeeds.
If you do not expect to build Rust software on the Pi again, you can also remove the Rust toolchain entirely:

```sh
rustup self uninstall
```

Or just clear downloaded dependencies and source code, but keeping the toolchain:

```sh
rm -rf ~/.cargo/registry ~/.cargo/git
```

After the binary and service file are in place, confirm the service exists:

```sh
systemctl status spotifyd.service
```

Create `/etc/spotifyd.conf` with a persistent cache path and the same advertised receiver name the jukebox app will target.
A minimal baseline is:

```toml
[global]
device_name = "jukebox"
backend = "alsa"
device = "default"
cache_path = "/var/cache/spotifyd"
use_mpris = false
volume_normalisation = false
```

Create the persistent cache directory and make it writable by the runtime user:

```sh
sudo mkdir -p /var/cache/spotifyd
sudo chown pi:pi /var/cache/spotifyd
```

Receiver-side auth is separate from the jukebox app's refresh token.
For this repo's EPIC 3 baseline, use `spotifyd`'s manual OAuth login flow and copy the resulting credential file onto the Pi.
Do not rely on a keyring-backed login for the system-wide `spotifyd.service`.

Use this sequence:

1. Finish `/etc/spotifyd.conf` on the Pi first, especially the final `cache_path`.
2. On a browser-capable machine, install a `spotifyd` binary and create a temporary `/etc/spotifyd.conf` that only sets a cache path.
This is the path that worked with the Homebrew macOS install used during bring-up:

```sh
mkdir -p /tmp/spotifyd-auth
sudo cp /etc/spotifyd.conf /etc/spotifyd.conf.bak 2>/dev/null || true
cat | sudo tee /etc/spotifyd.conf >/dev/null <<'EOF'
[global]
cache_path = "/tmp/spotifyd-auth"
EOF
```

3. On that same browser-capable machine, start the OAuth flow:

```sh
spotifyd authenticate
```

4. Open the URL printed by `spotifyd`, log in to Spotify, and approve the connection.
5. After the browser shows `Go back to your terminal :)`, confirm that the credential file now exists on the browser-capable machine:

```sh
ls -l /tmp/spotifyd-auth/oauth/credentials.json
```

6. Copy that file onto the Pi and place it under the Pi's configured cache path:

```sh
scp /tmp/spotifyd-auth/oauth/credentials.json pi@jukebox.local:/tmp/spotifyd-credentials.json
ssh pi@jukebox.local '
  sudo mkdir -p /var/cache/spotifyd/oauth &&
  sudo install -o pi -g pi -m 600 /tmp/spotifyd-credentials.json /var/cache/spotifyd/oauth/credentials.json &&
  rm -f /tmp/spotifyd-credentials.json
'
```

7. Back on the Pi, start the receiver and confirm it comes up cleanly:

```sh
sudo systemctl enable spotifyd.service
sudo systemctl restart spotifyd.service
sudo systemctl status spotifyd.service
```

8. Restore the browser-capable machine's original `spotifyd` config if you temporarily replaced it:

```sh
if [ -f /etc/spotifyd.conf.bak ]; then
  sudo mv /etc/spotifyd.conf.bak /etc/spotifyd.conf
else
  sudo rm -f /etc/spotifyd.conf
fi
```

If you change `cache_path` later, repeat the OAuth step and copy the credential file to the new location.

Keep the receiver-side session/cache material separate from `/etc/jukebox/jukebox.env`.
That env file is only for the Python app's controller-side Web API credentials and runtime settings.

## 5. Run the Bootstrap Helper

Run the repo bootstrap helper from your development machine only after `spotifyd.service` exists and `/etc/spotifyd.conf` includes a persistent `cache_path`:

```sh
JUKEBOX_PI_HOST=jukebox.local ./scripts/pi-bootstrap.sh
```

That script prepares `/opt/jukebox`, ensures `/etc/jukebox` exists, creates the configured `spotifyd` cache directory when needed, and copies the tracked env template into place if the real env file does not exist yet.

## 6. Configure and Verify USB Audio Output

The EPIC 3 baseline audio path is a USB sound card feeding an external powered speaker.
After plugging in the USB card and running `sudo raspi-config` to select USB audio, verify the audio path before deploying the jukebox service:

```sh
aplay -l
speaker-test -c 2 -t wav
aplay /usr/share/sounds/alsa/Front_Center.wav
```

`aplay -l` should show the USB sound card.
Use `speaker-test` to confirm that the default output reaches the external speaker, then use the `aplay` sample as a simple spoken confirmation.
If these commands do not produce sound, fix the Pi-side USB audio routing first and rerun the same checks before proceeding.

One important detail from bring-up: a per-user `/home/pi/.asoundrc` may make manual tests work for the `pi` user while `spotifyd.service` still stays silent.
To make the USB card the system-wide ALSA default for services as well, copy the working config into `/etc/asound.conf`:

```sh
sudo cp /home/pi/.asoundrc /etc/asound.conf
sudo systemctl restart spotifyd.service
```

Then test Spotify playback again through `spotifyd`.
Use `/etc/asound.conf` as the authoritative fix for service playback, not only `~/.asoundrc`.

Keep the Pi's 3.5 mm analog output only as a fallback troubleshooting path if the USB card is missing or fails.

## 7. Discover the Scanner Device Path

Plug in the USB scanner and identify the stable keyboard event path:

```sh
ls -l /dev/input/by-id
```

Look for the scanner entry ending in `-event-kbd`.
Store that exact path in `/etc/jukebox/jukebox.env` as `JUKEBOX_SCANNER_DEVICE`.

The EPIC 3 runtime expects the scanner to emit newline-terminated Spotify URI payloads.

## 8. Configure `/etc/jukebox/jukebox.env`

Start from the tracked template:

```sh
sudo cp /opt/jukebox/systemd/jukebox.env.example /etc/jukebox/jukebox.env
sudo chmod 640 /etc/jukebox/jukebox.env
```

Fill in:

- Spotify client ID
- Spotify client secret
- Spotify refresh token
- `JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME`
- `JUKEBOX_SCANNER_DEVICE`

Recommended EPIC 3 values:

```dotenv
JUKEBOX_INPUT_BACKEND=evdev
JUKEBOX_PLAYBACK_BACKEND=spotify
JUKEBOX_LOG_FORMAT=json
JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS=5.0
JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS=0.25
JUKEBOX_HEALTH_POLL_INTERVAL_SECONDS=5.0
```

The refresh token used by the Python app must include these Spotify Web API scopes:

- `user-read-playback-state`
- `user-modify-playback-state`

This token is controller-side API auth only.
It does not replace the receiver-side `spotifyd` session/bootstrap material.

Keep secrets out of the repository and out of committed files.

## 9. Deploy and Enable the Service

Use the deploy helper from your development machine:

```sh
JUKEBOX_PI_HOST=jukebox.local ./scripts/pi-deploy.sh
```

The deploy script installs the package into `/opt/jukebox/.venv`, refreshes the `systemd` unit, and restarts `jukebox.service`.

## 10. Confirm Boot-to-Ready and Degraded-State Behavior

After deployment, verify:

```sh
ssh pi@jukebox.local 'systemctl is-active spotifyd.service'
ssh pi@jukebox.local 'systemctl is-active jukebox.service'
ssh pi@jukebox.local 'journalctl -u jukebox.service -n 50 --no-pager'
```

For an EPIC 3-ready system:

- `spotifyd.service` is active
- `jukebox.service` is active
- the jukebox journal shows `[BOOT]`
- the runtime emits either `[READY]` or one clear degraded state while dependencies recover
- `ready` is reserved for a runtime that can actually complete autonomous scan-to-playback

The runtime health monitor may emit these degraded states while recovery is in progress:

- `scanner_unavailable`
- `controller_auth_unavailable`
- `network_unavailable`
- `receiver_unavailable`

Those degraded states are expected to be observable.
They are not equivalent to `ready`, and they should not force a restart loop.
