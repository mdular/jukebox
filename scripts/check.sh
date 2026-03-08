#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)

exec make -C "$PROJECT_ROOT" PYTHON="${PYTHON:-python3}" check
