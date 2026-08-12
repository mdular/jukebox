# Jukebox Card Maker spike

This directory is an isolated Python distribution for the adult-operated Card Maker.
It does not import or run the jukebox controller service.

## Local setup

```sh
cd cardmaker
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

Live use requires these server-side values:

```sh
export CARDMAKER_SPOTIFY_CLIENT_ID='...'
export CARDMAKER_SPOTIFY_CLIENT_SECRET='...'
export CARDMAKER_SPOTIFY_MARKET='DE'
.venv/bin/python -m cardmaker
```

The spike binds to `127.0.0.1:8081` by default. Optional process settings are
`CARDMAKER_HTTP_BIND`, `CARDMAKER_HTTP_PORT`, and `CARDMAKER_LOG_LEVEL`.

## Checks

```sh
cd cardmaker
.venv/bin/ruff check src tests tools
.venv/bin/mypy
.venv/bin/pytest
```

Generated cards remain in browser memory until downloaded; the server does not
create an artwork cache, card library, or output directory.
