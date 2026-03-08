#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)

if [ -n "${PYTHON:-}" ]; then
  exec make -C "$PROJECT_ROOT" PYTHON="$PYTHON" venv
fi

exec make -C "$PROJECT_ROOT" venv
