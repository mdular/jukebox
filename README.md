# Jukebox

EPIC 2 implementation for the Raspberry Pi QR card jukebox project.

The repository now supports both the local `stdin` development loop and the Raspberry Pi bring-up path defined for EPIC 2: Linux `evdev` scanner intake, Spotify target-device resolution plus playback confirmation, and `systemd`-based deployment around `raspotify`.

## Project Index

- Product and implementation specs live under [`spec/`](/Users/markus/Workspace/jukebox/spec).
- [`spec/concept.md`](/Users/markus/Workspace/jukebox/spec/concept.md) is the source of truth for product direction.
- Pi bring-up and operations live under [`docs/`](/Users/markus/Workspace/jukebox/docs):
  - [`docs/pi-setup.md`](/Users/markus/Workspace/jukebox/docs/pi-setup.md)
  - [`docs/pi-deploy.md`](/Users/markus/Workspace/jukebox/docs/pi-deploy.md)
  - [`docs/pi-validation.md`](/Users/markus/Workspace/jukebox/docs/pi-validation.md)

## Repository Layout

```text
docs/           Raspberry Pi setup, deploy, and validation guides
spec/           Project specifications
src/jukebox/    Application package
tests/          Automated tests
scripts/        Local and Pi deployment helpers
systemd/        Service unit and env template
```

## Local Development

Requirements:

- Python 3.11 or newer
- `make`
- a POSIX shell

Bootstrap a local virtual environment:

```sh
make venv
```

Run the local development loop:

```sh
make run
printf '%s\n' 'spotify:track:6rqhFgbbKwnb9MLmUQDhG6' | ./scripts/run-local.sh
```

Local validation commands:

```sh
make lint
make typecheck
make test
make check
```

## Runtime Configuration

Core variables:

- `JUKEBOX_ENV`
- `JUKEBOX_LOG_LEVEL`
- `JUKEBOX_LOG_FORMAT`
- `JUKEBOX_DUPLICATE_WINDOW_SECONDS`

Input variables:

- `JUKEBOX_INPUT_BACKEND`: `stdin` or `evdev`, defaults to `stdin`
- `JUKEBOX_SCANNER_DEVICE`: required when `JUKEBOX_INPUT_BACKEND=evdev`

Playback variables:

- `JUKEBOX_PLAYBACK_BACKEND`: `stub` or `spotify`, defaults to `stub`
- `JUKEBOX_SPOTIFY_CLIENT_ID`
- `JUKEBOX_SPOTIFY_CLIENT_SECRET`
- `JUKEBOX_SPOTIFY_REFRESH_TOKEN`
- `JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME`: required for the EPIC 2 Pi path unless `JUKEBOX_SPOTIFY_DEVICE_ID` is set
- `JUKEBOX_SPOTIFY_DEVICE_ID`: optional override for troubleshooting
- `JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS`: defaults to `5.0`
- `JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS`: defaults to `0.25`

For Raspberry Pi deployment, start from [`systemd/jukebox.env.example`](/Users/markus/Workspace/jukebox/systemd/jukebox.env.example) and place the real file at `/etc/jukebox/jukebox.env`.

## Raspberry Pi Workflow

Use the Pi helpers from your development machine:

```sh
JUKEBOX_PI_HOST=jukebox.local ./scripts/pi-bootstrap.sh
JUKEBOX_PI_HOST=jukebox.local ./scripts/pi-deploy.sh
JUKEBOX_PI_HOST=jukebox.local \
JUKEBOX_SMOKE_URI='spotify:track:6rqhFgbbKwnb9MLmUQDhG6' \
./scripts/pi-smoke.sh
```

The full operational flow is documented in [`docs/pi-setup.md`](/Users/markus/Workspace/jukebox/docs/pi-setup.md), [`docs/pi-deploy.md`](/Users/markus/Workspace/jukebox/docs/pi-deploy.md), and [`docs/pi-validation.md`](/Users/markus/Workspace/jukebox/docs/pi-validation.md).
The current prototype's concrete bring-up findings are recorded in [`docs/pi-setup-log.md`](/Users/markus/Workspace/jukebox/docs/pi-setup-log.md).

For EPIC 2 hardware validation, the default external-speaker path is now a USB sound card on the Pi rather than the 3.5 mm analog output.

## Runtime Notes

- `python -m jukebox` is the canonical entrypoint.
- The controller emits boot, ready, scan, duplicate, validation, and playback outcome events.
- Under `systemd`, stdout and stderr are designed to be useful in `journalctl`.
- `systemd/jukebox.service` is the EPIC 2 service baseline for Raspberry Pi OS.
