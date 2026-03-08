#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PYTHON_RESOLVER=$PROJECT_ROOT/scripts/resolve-python.sh

if [ -n "${PYTHON:-}" ]; then
  PYTHON_BIN=$PYTHON
elif [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  PYTHON_BIN=$PROJECT_ROOT/.venv/bin/python
else
  PYTHON_BIN=$("$PYTHON_RESOLVER")
fi

PYTHON="$PYTHON_BIN" "$PYTHON_RESOLVER" >/dev/null

if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a
  . "$PROJECT_ROOT/.env"
  set +a
fi

PYTHONPATH="$PROJECT_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" exec "$PYTHON_BIN" -m jukebox "$@"
