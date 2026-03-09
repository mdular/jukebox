#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)

PI_HOST=${JUKEBOX_PI_HOST:?Set JUKEBOX_PI_HOST to the Raspberry Pi hostname or IP.}
PI_USER=${JUKEBOX_PI_USER:-pi}
PI_PORT=${JUKEBOX_PI_PORT:-22}
PI_ROOT=${JUKEBOX_PI_ROOT:-/opt/jukebox}
RECEIVER_SERVICE_NAME=${JUKEBOX_PI_RECEIVER_SERVICE_NAME:-spotifyd.service}

SSH_TARGET=$PI_USER@$PI_HOST

scp -P "$PI_PORT" "$PROJECT_ROOT/systemd/jukebox.env.example" \
  "$SSH_TARGET:/tmp/jukebox.env.example"

ssh -p "$PI_PORT" "$SSH_TARGET" /bin/sh <<EOF
set -eu
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-dev build-essential libevdev-dev alsa-utils
if ! systemctl list-unit-files | grep -q '^$RECEIVER_SERVICE_NAME'; then
  echo '$RECEIVER_SERVICE_NAME is not installed. Finish the receiver setup in docs/pi-setup.md before bootstrap.' >&2
  exit 1
fi
if [ '$RECEIVER_SERVICE_NAME' = 'spotifyd.service' ]; then
  if [ ! -f /etc/spotifyd.conf ]; then
    echo '/etc/spotifyd.conf is missing. Finish the spotifyd configuration in docs/pi-setup.md before bootstrap.' >&2
    exit 1
  fi
  cache_path=\$(awk -F= '/^[[:space:]]*cache_path[[:space:]]*=/{print \$2; exit}' /etc/spotifyd.conf | sed 's/[[:space:]"]//g')
  if [ -z "\$cache_path" ]; then
    echo 'spotifyd.conf is missing cache_path. Configure a persistent cache path before bootstrap.' >&2
    exit 1
  fi
  sudo mkdir -p "\$cache_path"
  sudo chown '$PI_USER':'$PI_USER' "\$cache_path"
fi
sudo mkdir -p '$PI_ROOT' /etc/jukebox
sudo chown '$PI_USER':'$PI_USER' '$PI_ROOT'
if [ ! -f /etc/jukebox/jukebox.env ]; then
  sudo install -m 640 /tmp/jukebox.env.example /etc/jukebox/jukebox.env
  echo 'Created /etc/jukebox/jukebox.env from the example template.'
fi
rm -f /tmp/jukebox.env.example
EOF
