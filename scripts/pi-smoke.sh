#!/bin/sh
set -eu

PI_HOST=${JUKEBOX_PI_HOST:?Set JUKEBOX_PI_HOST to the Raspberry Pi hostname or IP.}
PI_USER=${JUKEBOX_PI_USER:-pi}
PI_PORT=${JUKEBOX_PI_PORT:-22}
PI_ROOT=${JUKEBOX_PI_ROOT:-/opt/jukebox}
RECEIVER_SERVICE_NAME=${JUKEBOX_PI_RECEIVER_SERVICE_NAME:-spotifyd.service}
SMOKE_URI=${JUKEBOX_SMOKE_URI:-}
SMOKE_ACTION_PAYLOAD=${JUKEBOX_SMOKE_ACTION_PAYLOAD:-}
SMOKE_REBOOT=${JUKEBOX_SMOKE_REBOOT:-0}
SMOKE_REBOOT_COUNT=${JUKEBOX_SMOKE_REBOOT_COUNT:-1}

SSH_TARGET=$PI_USER@$PI_HOST
overall_status=0

print_unit_state() {
  unit_name=$1
  echo "==> systemctl is-active $unit_name"
  ssh -p "$PI_PORT" "$SSH_TARGET" "systemctl is-active '$unit_name' || true"
}

print_status_json() {
  echo "==> operator status JSON"
ssh -p "$PI_PORT" "$SSH_TARGET" /bin/sh <<EOF
set -eu
sudo /bin/sh <<'SH'
set -eu
set -a
. /etc/jukebox/jukebox.env
set +a
'$PI_ROOT/.venv/bin/python' - <<'PY'
import json
import os
from urllib.request import urlopen

port = os.environ.get("JUKEBOX_OPERATOR_HTTP_PORT", "8080")
url = f"http://127.0.0.1:{port}/status.json"
with urlopen(url, timeout=5) as response:
    payload = json.loads(response.read().decode("utf-8"))
print(json.dumps(payload, indent=2, sort_keys=True))
PY
SH
EOF
}

run_replay() {
  payload=$1
  echo "==> stdin replay: $payload"
  replay_output=$(ssh -p "$PI_PORT" "$SSH_TARGET" /bin/sh <<EOF 2>&1
set -eu
cd '$PI_ROOT'
sudo /bin/sh <<'SH'
set -eu
set -a
. /etc/jukebox/jukebox.env
set +a
printf '%s\n' '$payload' | JUKEBOX_INPUT_BACKEND=stdin JUKEBOX_OPERATOR_HTTP_PORT=18080 '$PI_ROOT/.venv/bin/python' -m jukebox
SH
EOF
)
  printf '%s\n' "$replay_output"

  case "$replay_output" in
    *"[PLAYBACK spotify] started"*|*"[QUEUE spotify] queued track"*|*"[ACTION]"*)
      ;;
    *)
      overall_status=1
      ;;
  esac
}

run_smoke_iteration() {
  print_unit_state "$RECEIVER_SERVICE_NAME"
  print_unit_state jukebox.service

  echo "==> journalctl -u $RECEIVER_SERVICE_NAME -n 50 --no-pager"
  ssh -p "$PI_PORT" "$SSH_TARGET" "journalctl -u '$RECEIVER_SERVICE_NAME' -n 50 --no-pager"

  echo "==> journalctl -u jukebox.service -n 50 --no-pager"
  ssh -p "$PI_PORT" "$SSH_TARGET" "journalctl -u jukebox.service -n 50 --no-pager"

  if ! print_status_json; then
    overall_status=1
  fi

  if [ -n "$SMOKE_URI" ]; then
    run_replay "$SMOKE_URI"
  fi
  if [ -n "$SMOKE_ACTION_PAYLOAD" ]; then
    run_replay "$SMOKE_ACTION_PAYLOAD"
  fi
}

run_smoke_iteration

if [ "$SMOKE_REBOOT" != "1" ]; then
  exit "$overall_status"
fi

sleep 5
iteration=1
while [ "$iteration" -le "$SMOKE_REBOOT_COUNT" ]; do
  echo "==> reboot iteration $iteration of $SMOKE_REBOOT_COUNT"
  ssh -p "$PI_PORT" "$SSH_TARGET" "sudo reboot" || true
  sleep 5

  while ! ssh -p "$PI_PORT" -o ConnectTimeout=5 "$SSH_TARGET" "true" >/dev/null 2>&1; do
    sleep 5
  done

  run_smoke_iteration
  iteration=$((iteration + 1))
done

exit "$overall_status"
