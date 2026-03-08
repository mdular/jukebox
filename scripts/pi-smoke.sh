#!/bin/sh
set -eu

PI_HOST=${JUKEBOX_PI_HOST:?Set JUKEBOX_PI_HOST to the Raspberry Pi hostname or IP.}
PI_USER=${JUKEBOX_PI_USER:-pi}
PI_PORT=${JUKEBOX_PI_PORT:-22}
PI_ROOT=${JUKEBOX_PI_ROOT:-/opt/jukebox}
SMOKE_URI=${JUKEBOX_SMOKE_URI:-}
SMOKE_REBOOT=${JUKEBOX_SMOKE_REBOOT:-0}

SSH_TARGET=$PI_USER@$PI_HOST

ssh -p "$PI_PORT" "$SSH_TARGET" "systemctl is-active raspotify.service"
ssh -p "$PI_PORT" "$SSH_TARGET" "systemctl is-active jukebox.service"
ssh -p "$PI_PORT" "$SSH_TARGET" "journalctl -u jukebox.service -n 50 --no-pager"

if [ -n "$SMOKE_URI" ]; then
  ssh -p "$PI_PORT" "$SSH_TARGET" \
    "set -eu
    cd '$PI_ROOT'
    set -a
    . /etc/jukebox/jukebox.env
    set +a
    printf '%s\n' '$SMOKE_URI' | JUKEBOX_INPUT_BACKEND=stdin '$PI_ROOT/.venv/bin/python' -m jukebox"
fi

if [ "$SMOKE_REBOOT" != "1" ]; then
  exit 0
fi

ssh -p "$PI_PORT" "$SSH_TARGET" "sudo reboot" || true
sleep 5

while ! ssh -p "$PI_PORT" -o ConnectTimeout=5 "$SSH_TARGET" "true" >/dev/null 2>&1; do
  sleep 5
done

ssh -p "$PI_PORT" "$SSH_TARGET" "systemctl is-active raspotify.service"
ssh -p "$PI_PORT" "$SSH_TARGET" "systemctl is-active jukebox.service"
