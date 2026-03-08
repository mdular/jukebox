# Jukebox

Technical scaffold for the Raspberry Pi QR card jukebox project.

The repository currently contains project setup only. Scanner handling, Spotify playback, controller logic, and GPIO support are intentionally not implemented yet.

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
src/jukebox/    Python package scaffold
tests/          Automated test scaffold
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

## Runtime Notes

- `python -m jukebox` is the canonical module entrypoint.
- The current scaffold configures logging, emits one startup message, and exits successfully.
- No Spotify authentication flow, scanner parsing, controller loop, or GPIO integration is included yet.

## systemd Scaffold

[`systemd/jukebox.service`](/Users/markus/Workspace/jukebox/systemd/jukebox.service) is a deployment scaffold for Raspberry Pi OS.

It currently assumes:

- `User=pi`
- `WorkingDirectory=/opt/jukebox`
- `ExecStart=/opt/jukebox/.venv/bin/python -m jukebox`
- `EnvironmentFile=/etc/jukebox/jukebox.env`

The unit is intentionally incomplete for production use because the application is not a long-running daemon yet.
