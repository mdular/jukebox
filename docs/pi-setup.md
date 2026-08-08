# Raspberry Pi Setup

This is the authoritative EPIC 4 bring-up guide for a fresh Raspberry Pi 3 running Raspberry Pi OS Lite.
It carries forward the stabilized EPIC 3 receiver baseline and adds the EPIC 4 operator/auth flows, control-card runtime, and passive-status behavior.

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
For the current prototype parts and scanner-specific notes, see [docs/pi-build.md](/Users/markus/Workspace/jukebox/docs/pi-build.md).

## EPIC 4 Maintenance Additions

The EPIC 4 runtime adds:

- a maintenance HTTP surface on `JUKEBOX_OPERATOR_HTTP_PORT`
- operator and control cards under the `jukebox:<group>:<action>` namespace
- persisted non-secret state under `/var/lib/jukebox/state.json`
- helper-script install targets under `/usr/local/libexec`
- a `sudoers` policy file for Wi-Fi, auth, and shutdown helper commands

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

EPIC 4 also expects `/var/lib/jukebox` to exist and the helper scripts from `scripts/runtime/` to be installed under `/usr/local/libexec`. The bootstrap script now installs those assets and the matching `sudoers` entry.

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
volume_normalisation = true
```

Create the persistent cache directory and make it writable by the runtime user:

```sh
sudo mkdir -p /var/cache/spotifyd
sudo chown pi:pi /var/cache/spotifyd
```

Receiver-side auth is separate from the jukebox app's refresh token.
For the EPIC 4 baseline, use the helper-owned auth flow exposed by the runtime instead of manually copying credential files from another machine.
Do not rely on a keyring-backed login for the system-wide `spotifyd.service`.

Use this sequence:

1. Finish `/etc/spotifyd.conf` on the Pi first, especially the final `cache_path`.
2. Bootstrap and deploy the repo so `/usr/local/libexec/jukebox-spotifyd-auth-helper` and the operator HTTP surface are installed.
3. Confirm `/etc/jukebox/jukebox.env` includes:
   - `JUKEBOX_OPERATOR_HTTP_BIND=0.0.0.0`
   - `JUKEBOX_OPERATOR_HTTP_PORT`
   - `JUKEBOX_SPOTIFYD_AUTH_HELPER_COMMAND=/usr/local/libexec/jukebox-spotifyd-auth-helper`
4. Start the services:

```sh
sudo systemctl enable spotifyd.service
sudo systemctl restart spotifyd.service
sudo systemctl restart jukebox.service
sudo systemctl status spotifyd.service
sudo systemctl status jukebox.service
```

5. From another browser-capable device on the same network, open:

```text
http://<pi-host>:<operator-port>/auth
```

6. Start the auth flow from the browser page.
7. If the helper surfaces an approval URL, open it in the browser, log in to Spotify, and approve the receiver.
8. Refresh `/auth` and `status.json` until the helper reports success and the runtime clears `auth_required`.

If you change `cache_path` later, rerun the same browser auth flow so `spotifyd authenticate` can refresh the receiver-side session material in the new location.

Keep the receiver-side session/cache material separate from `/etc/jukebox/jukebox.env`.
That env file is only for the Python app's controller-side Web API credentials and runtime settings.

## 5. Run the Bootstrap Helper

Run the repo bootstrap helper from your development machine only after `spotifyd.service` exists and `/etc/spotifyd.conf` includes a persistent `cache_path`:

```sh
JUKEBOX_PI_HOST=jukebox.local ./scripts/pi-bootstrap.sh
```

That script prepares `/opt/jukebox`, ensures `/etc/jukebox` exists, creates the configured `spotifyd` cache directory when needed, and copies the tracked env template into place if the real env file does not exist yet.

## 6. Configure and Verify USB Audio Output

The current baseline audio path is a USB sound card feeding an XY-AP50L amplifier and one Pioneer TS-G1320F speaker.
After plugging in the USB card and running `sudo raspi-config` to select USB audio, verify the audio path before deploying the jukebox service:

```sh
aplay -l
speaker-test -c 2 -t wav
aplay /usr/share/sounds/alsa/Front_Center.wav
```

`aplay -l` should show the USB sound card.
Use `speaker-test` to confirm that the default output is audible through the mono amp-and-speaker path, then use the `aplay` sample as a simple spoken confirmation.
If these commands do not produce sound, fix the Pi-side USB audio routing first and rerun the same checks before proceeding.

One important detail from bring-up: a per-user `/home/pi/.asoundrc` may make manual tests work for the `pi` user while `spotifyd.service` still stays silent.
The current prototype instead relies on a custom `/etc/asound.conf` that both selects the USB sound card for services and mixes stereo down to the single speaker on the amplifier's left output.

Treat `/etc/asound.conf` as an operator-managed part of the audio baseline:

```
pcm.!default {
  type plug
  slave.pcm "mono_left"
}

pcm.mono_left {
  type route
  slave {
    pcm "hw:1,0"
    channels 2
  }

  ttable {
    0.0 0.5
    1.0 0.5
  }
}

ctl.!default {
  type hw
  card 1
}
```

- if the Pi already has the working mono mixdown file, keep it and do not overwrite it with a stale `~/.asoundrc`
- the bootstrap and deploy helpers do not install or replace `/etc/asound.conf`
- after changing `/etc/asound.conf`, restart `spotifyd.service` and rerun the same `speaker-test` and `aplay` checks

Use `/etc/asound.conf` as the authoritative service-level ALSA config, not only `~/.asoundrc`.

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

Recommended EPIC 4 values:

```dotenv
JUKEBOX_INPUT_BACKEND=evdev
JUKEBOX_PLAYBACK_BACKEND=spotify
JUKEBOX_LOG_FORMAT=json
JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS=5.0
JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS=0.25
JUKEBOX_SPOTIFY_DEVICE_PROBE_RETRY_COUNT=5
JUKEBOX_SPOTIFY_DEVICE_PROBE_RETRY_INTERVAL_SECONDS=2.0
JUKEBOX_HEALTH_POLL_INTERVAL_SECONDS=15.0
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
- `spotify_rate_limited`
- `network_unavailable`
- `receiver_unavailable`

Those degraded states are expected to be observable.
They are not equivalent to `ready`, and they should not force a restart loop.
