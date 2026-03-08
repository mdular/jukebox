#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)

PI_HOST=${JUKEBOX_PI_HOST:?Set JUKEBOX_PI_HOST to the Raspberry Pi hostname or IP.}
PI_USER=${JUKEBOX_PI_USER:-pi}
PI_PORT=${JUKEBOX_PI_PORT:-22}
PI_ROOT=${JUKEBOX_PI_ROOT:-/opt/jukebox}

SSH_TARGET=$PI_USER@$PI_HOST

scp -P "$PI_PORT" "$PROJECT_ROOT/systemd/jukebox.env.example" \
  "$SSH_TARGET:/tmp/jukebox.env.example"

ssh -p "$PI_PORT" "$SSH_TARGET" \
  "set -eu
  sudo apt-get update
  sudo apt-get install -y python3-venv python3-pip python3-dev build-essential libevdev-dev alsa-utils
  if ! systemctl list-unit-files | grep -q '^raspotify.service'; then
    echo 'raspotify.service is not installed. Finish the raspotify step in docs/pi-setup.md before bootstrap.' >&2
    exit 1
  fi
  sudo mkdir -p '$PI_ROOT' /etc/jukebox
  sudo chown '$PI_USER':'$PI_USER' '$PI_ROOT'
  if [ ! -f /etc/jukebox/jukebox.env ]; then
    sudo install -m 640 /tmp/jukebox.env.example /etc/jukebox/jukebox.env
    echo 'Created /etc/jukebox/jukebox.env from the example template.'
  fi
  rm -f /tmp/jukebox.env.example"
