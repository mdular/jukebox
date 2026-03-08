#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)

PI_HOST=${JUKEBOX_PI_HOST:?Set JUKEBOX_PI_HOST to the Raspberry Pi hostname or IP.}
PI_USER=${JUKEBOX_PI_USER:-pi}
PI_PORT=${JUKEBOX_PI_PORT:-22}
PI_ROOT=${JUKEBOX_PI_ROOT:-/opt/jukebox}

SSH_TARGET=$PI_USER@$PI_HOST
ARCHIVE=/tmp/jukebox-deploy.tgz

rm -f "$ARCHIVE"
tar -czf "$ARCHIVE" \
  --exclude .git \
  --exclude .venv \
  --exclude .mypy_cache \
  --exclude .pytest_cache \
  --exclude .ruff_cache \
  --exclude __pycache__ \
  --exclude '*.pyc' \
  --exclude '.env' \
  -C "$PROJECT_ROOT" .

scp -P "$PI_PORT" "$ARCHIVE" "$SSH_TARGET:/tmp/jukebox-deploy.tgz"

ssh -p "$PI_PORT" "$SSH_TARGET" \
  "set -eu
  mkdir -p '$PI_ROOT'
  tar -xzf /tmp/jukebox-deploy.tgz -C '$PI_ROOT'
  python3 -m venv '$PI_ROOT/.venv'
  '$PI_ROOT/.venv/bin/pip' install --upgrade pip
  cd '$PI_ROOT'
  '$PI_ROOT/.venv/bin/pip' install -e '.[pi]'
  sudo install -m 644 '$PI_ROOT/systemd/jukebox.service' /etc/systemd/system/jukebox.service
  if [ ! -f /etc/jukebox/jukebox.env ]; then
    echo '/etc/jukebox/jukebox.env is missing. Run scripts/pi-bootstrap.sh first.' >&2
    exit 1
  fi
  sudo systemctl daemon-reload
  sudo systemctl enable jukebox.service
  sudo systemctl restart jukebox.service
  rm -f /tmp/jukebox-deploy.tgz"

rm -f "$ARCHIVE"
