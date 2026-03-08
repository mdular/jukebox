# Raspberry Pi Deploy

This document describes the repeatable SSH/SCP deployment workflow for EPIC 2.

## Remote Layout

The supported Pi layout is:

- `/opt/jukebox` for the repo working tree
- `/opt/jukebox/.venv` for the runtime virtualenv
- `/etc/jukebox/jukebox.env` for runtime configuration and secrets
- `/etc/systemd/system/jukebox.service` for the service unit

## Required Local Environment Variables

The deployment scripts read:

- `JUKEBOX_PI_HOST` required
- `JUKEBOX_PI_USER` optional, defaults to `pi`
- `JUKEBOX_PI_PORT` optional, defaults to `22`
- `JUKEBOX_PI_ROOT` optional, defaults to `/opt/jukebox`

`scripts/pi-smoke.sh` also reads:

- `JUKEBOX_SMOKE_URI` optional one-shot Spotify URI for remote smoke playback
- `JUKEBOX_SMOKE_REBOOT=1` optional flag to include a clean reboot check

## Bootstrap Once

Run the initial bootstrap after the Pi is reachable over SSH, `raspotify` is installed, and the USB audio path has already been verified:

```sh
JUKEBOX_PI_HOST=jukebox.local ./scripts/pi-bootstrap.sh
```

That step installs baseline system packages, creates `/opt/jukebox`, and seeds `/etc/jukebox/jukebox.env` from the tracked example when necessary.

## Deploy the Current Working Tree

Deploy the repo contents and restart the service:

```sh
JUKEBOX_PI_HOST=jukebox.local ./scripts/pi-deploy.sh
```

The deploy helper:

1. creates a tarball from the current working tree while excluding local caches, the local virtualenv, and `.env`
2. copies that archive to the Pi with `scp`
3. unpacks it under `/opt/jukebox`
4. installs the package into `/opt/jukebox/.venv` with the `.[pi]` extra
5. refreshes `/etc/systemd/system/jukebox.service`
6. reloads `systemd`, enables the service, and restarts it

The deploy path assumes `/etc/jukebox/jukebox.env` already exists and contains real secrets.

## Smoke and Reboot Validation

Check services, logs, and optionally run a one-shot playback smoke test:

```sh
JUKEBOX_PI_HOST=jukebox.local \
JUKEBOX_SMOKE_URI='spotify:track:6rqhFgbbKwnb9MLmUQDhG6' \
./scripts/pi-smoke.sh
```

Include a reboot in the same flow:

```sh
JUKEBOX_PI_HOST=jukebox.local \
JUKEBOX_SMOKE_URI='spotify:track:6rqhFgbbKwnb9MLmUQDhG6' \
JUKEBOX_SMOKE_REBOOT=1 \
./scripts/pi-smoke.sh
```

The smoke helper temporarily overrides `JUKEBOX_INPUT_BACKEND=stdin` for the one-shot URI replay so the deployed runtime, Spotify auth, target-device resolution, and playback-confirmation path can be validated remotely.
