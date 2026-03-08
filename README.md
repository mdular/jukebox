# Jukebox

Local EPIC 1 implementation for the Raspberry Pi QR card jukebox project.

The repository now contains the line-based scan controller loop, strict Spotify URI parsing, duplicate suppression, terminal feedback, structured logging, a stub playback backend, and an optional Spotify playback backend. Raspberry Pi deployment and GPIO work are still intentionally out of scope here.

## Authoritative Specs

- All project specs live under [`spec/`](/Users/markus/Workspace/jukebox/spec).
- [`spec/concept.md`](/Users/markus/Workspace/jukebox/spec/concept.md) is the source of truth for product direction.
- Implementation changes should follow the specs and update documentation when structure or developer workflow changes.

## Requirements

- Python 3.11 or newer
- `make`
- A POSIX shell

Bootstrap commands auto-detect a supported Python interpreter when possible. If none is available on `PATH`, rerun with an explicit interpreter:

```sh
PYTHON=/path/to/python3.11 make venv
```

## Repository Layout

```text
spec/           Project specifications
src/jukebox/    Application package
tests/          Automated tests and replay fixtures
scripts/        Local utility scripts
systemd/        systemd unit scaffold
```

## Local Setup

Create a virtual environment and install the package in editable mode with development tools:

```sh
make venv
```

`make venv` and `./scripts/bootstrap.sh` use the same interpreter resolution logic. They first honor `PYTHON` when it is set, otherwise they search common `python3.x` command names and fail with an actionable message if nothing compatible is found.

Optional local environment file:

```sh
cp .env.example .env
```

`make run` sources `.env` if it exists, then runs `python -m jukebox`.

## Developer Commands

```sh
make run
make lint
make typecheck
make test
make check
```

Utility wrappers are also available:

```sh
./scripts/bootstrap.sh
./scripts/run-local.sh
./scripts/check.sh
```

If your machine's default `python3` is older than 3.11, keep using the same commands and set `PYTHON` explicitly:

```sh
PYTHON=/path/to/python3.11 make venv
PYTHON=/path/to/python3.11 ./scripts/bootstrap.sh
```

## Environment Variables

Current scaffold variables:

- `JUKEBOX_ENV`: free-form environment label, defaults to `development`
- `JUKEBOX_LOG_LEVEL`: standard log level, defaults to `INFO`
- `JUKEBOX_LOG_FORMAT`: `console` or `json`, defaults to `console`

Application-owned variables use the `JUKEBOX_` prefix. Future secrets must remain environment-driven and should only be added when required by the specs.

EPIC 1 runtime variables:

- `JUKEBOX_PLAYBACK_BACKEND`: `stub` or `spotify`, defaults to `stub`
- `JUKEBOX_DUPLICATE_WINDOW_SECONDS`: positive float, defaults to `2.0`
- `JUKEBOX_SPOTIFY_CLIENT_ID`: required when `JUKEBOX_PLAYBACK_BACKEND=spotify`
- `JUKEBOX_SPOTIFY_CLIENT_SECRET`: required when `JUKEBOX_PLAYBACK_BACKEND=spotify`
- `JUKEBOX_SPOTIFY_REFRESH_TOKEN`: required when `JUKEBOX_PLAYBACK_BACKEND=spotify`
- `JUKEBOX_SPOTIFY_DEVICE_ID`: optional Spotify target device

### Spotify Refresh Token

For local Spotify playback tests, use a one-time authorization-code flow and the loopback callback below:

```text
http://127.0.0.1:8000/callback
```

The example auth URL and token exchange command live in [examples.md](/Users/markus/Workspace/jukebox/spec/examples.md).

## Local Validation

The controller consumes newline-terminated scan payloads from `stdin`. That supports both manual input and keyboard-wedge USB scanners without changing the core loop.

Examples:

```sh
printf '%s\n' 'spotify:track:6rqhFgbbKwnb9MLmUQDhG6' | ./scripts/run-local.sh
./scripts/run-local.sh < tests/fixtures/scan_streams/happy_path.txt
JUKEBOX_PLAYBACK_BACKEND=spotify ./scripts/run-local.sh
```

Runtime behavior:

- stdout shows terminal states such as `IDLE`, `SCAN`, `ACCEPTED`, `DUPLICATE`, and playback outcomes
- stderr carries application logs according to `JUKEBOX_LOG_FORMAT`
- EOF exits with status `0`
- `Ctrl+C` exits with status `130`

## Runtime Notes

- `python -m jukebox` is the canonical module entrypoint.
- The application emits an initial idle state, then processes one scan per newline until EOF or interrupt.
- Valid payloads are strict Spotify URIs for `track`, `album`, and `playlist`.
- Duplicate suppression uses exact payload matching over the configured time window.
- The default playback backend is the local stub backend.
- The Spotify backend is optional and uses the Spotify Web API through environment-supplied credentials.
- GPIO integration is still not included.

## systemd Scaffold

[`systemd/jukebox.service`](/Users/markus/Workspace/jukebox/systemd/jukebox.service) is a deployment scaffold for Raspberry Pi OS.

It currently assumes:

- `User=pi`
- `WorkingDirectory=/opt/jukebox`
- `ExecStart=/opt/jukebox/.venv/bin/python -m jukebox`
- `EnvironmentFile=/etc/jukebox/jukebox.env`

The unit remains intentionally incomplete for production use because Raspberry Pi deployment, environment placement, and service hardening are not finalized in this repo.
