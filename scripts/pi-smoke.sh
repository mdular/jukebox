#!/bin/sh
set -eu

PI_HOST=${JUKEBOX_PI_HOST:?Set JUKEBOX_PI_HOST to the Raspberry Pi hostname or IP.}
PI_USER=${JUKEBOX_PI_USER:-pi}
PI_PORT=${JUKEBOX_PI_PORT:-22}
PI_ROOT=${JUKEBOX_PI_ROOT:-/opt/jukebox}
RECEIVER_SERVICE_NAME=${JUKEBOX_PI_RECEIVER_SERVICE_NAME:-spotifyd.service}
SMOKE_URI=${JUKEBOX_SMOKE_URI:-}
SMOKE_REBOOT=${JUKEBOX_SMOKE_REBOOT:-0}
SMOKE_REBOOT_COUNT=${JUKEBOX_SMOKE_REBOOT_COUNT:-1}

SSH_TARGET=$PI_USER@$PI_HOST
overall_status=0
receiver_status_ok=1
replay_status_ok=1

print_unit_state() {
  unit_name=$1

  echo "==> systemctl is-active $unit_name"
  unit_state=$(ssh -p "$PI_PORT" "$SSH_TARGET" "systemctl is-active '$unit_name'" || true)
  printf '%s\n' "$unit_state"
}

print_receiver_visibility() {
  echo "==> Spotify receiver visibility snapshot"
  ssh -p "$PI_PORT" "$SSH_TARGET" /bin/sh <<EOF
set -eu
cd '$PI_ROOT'
sudo /bin/sh <<'SH'
set -eu
set -a
. /etc/jukebox/jukebox.env
set +a
'$PI_ROOT/.venv/bin/python' - <<'PY'
import base64
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def emit(status_code, reason_code, message, *, device_name=None, devices=None, target_visible=None):
    payload = {
        "device_name": device_name,
        "devices": devices,
        "message": message,
        "reason_code": reason_code,
        "status_code": status_code,
        "target_visible": target_visible,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(0 if status_code == "ready" else 1)


required = (
    "JUKEBOX_SPOTIFY_CLIENT_ID",
    "JUKEBOX_SPOTIFY_CLIENT_SECRET",
    "JUKEBOX_SPOTIFY_REFRESH_TOKEN",
)
missing = [key for key in required if not os.environ.get(key)]
if missing:
    emit(
        "controller_auth_unavailable",
        "spotify_api_auth_error",
        "missing env: " + ", ".join(missing),
    )

target_name = os.environ.get("JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME")
target_device_id = os.environ.get("JUKEBOX_SPOTIFY_DEVICE_ID")
if not target_name and not target_device_id:
    emit(
        "controller_auth_unavailable",
        "spotify_api_auth_error",
        "JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME or JUKEBOX_SPOTIFY_DEVICE_ID must be set.",
    )

credentials = "{client_id}:{client_secret}".format(
    client_id=os.environ["JUKEBOX_SPOTIFY_CLIENT_ID"],
    client_secret=os.environ["JUKEBOX_SPOTIFY_CLIENT_SECRET"],
).encode("utf-8")
encoded_credentials = base64.b64encode(credentials).decode("ascii")

token_request = Request(
    "https://accounts.spotify.com/api/token",
    data=urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": os.environ["JUKEBOX_SPOTIFY_REFRESH_TOKEN"],
        }
    ).encode("ascii"),
    headers={
        "Authorization": "Basic " + encoded_credentials,
        "Content-Type": "application/x-www-form-urlencoded",
    },
    method="POST",
)

try:
    with urlopen(token_request, timeout=5) as response:
        token_payload = json.loads(response.read().decode("utf-8"))
except HTTPError as exc:
    emit(
        "controller_auth_unavailable" if exc.code in {400, 401, 403} else "network_unavailable",
        "spotify_api_auth_error" if exc.code in {400, 401, 403} else "network_discovery_failed",
        "token refresh failed with HTTP {code}".format(code=exc.code),
    )
except URLError as exc:
    emit(
        "network_unavailable",
        "network_discovery_failed",
        "token refresh transport error: {reason}".format(reason=exc.reason),
    )

access_token = token_payload.get("access_token")
if not isinstance(access_token, str) or access_token == "":
    emit(
        "controller_auth_unavailable",
        "spotify_api_auth_error",
        "token refresh response did not include an access token",
    )

devices_request = Request(
    "https://api.spotify.com/v1/me/player/devices",
    headers={"Authorization": "Bearer " + access_token},
    method="GET",
)

try:
    with urlopen(devices_request, timeout=5) as response:
        devices_payload = json.loads(response.read().decode("utf-8"))
except HTTPError as exc:
    emit(
        "controller_auth_unavailable" if exc.code in {401, 403} else "network_unavailable",
        "spotify_api_auth_error" if exc.code in {401, 403} else "network_discovery_failed",
        "devices request failed with HTTP {code}".format(code=exc.code),
    )
except URLError as exc:
    emit(
        "network_unavailable",
        "network_discovery_failed",
        "devices request transport error: {reason}".format(reason=exc.reason),
    )

devices = devices_payload.get("devices")
if not isinstance(devices, list):
    emit(
        "network_unavailable",
        "network_discovery_failed",
        "devices response did not include a device list",
    )

matched_device = None
for device in devices:
    if not isinstance(device, dict):
        continue
    raw_device_id = device.get("id")
    raw_name = device.get("name")
    if target_device_id:
        if raw_device_id == target_device_id:
            matched_device = device
            break
        continue
    if raw_name == target_name:
        matched_device = device
        break

if matched_device is None:
    emit(
        "receiver_unavailable",
        "device_not_listed",
        "configured receiver is not visible in Spotify devices",
        device_name=target_name or target_device_id,
        devices=devices,
        target_visible=False,
    )

emit(
    "ready",
    None,
    "configured receiver is visible in Spotify devices",
    device_name=matched_device.get("name"),
    devices=devices,
    target_visible=True,
)
PY
SH
EOF
}

print_remote_state() {
  print_unit_state "$RECEIVER_SERVICE_NAME"
  print_unit_state jukebox.service

  echo "==> journalctl -u $RECEIVER_SERVICE_NAME -n 50 --no-pager"
  ssh -p "$PI_PORT" "$SSH_TARGET" "journalctl -u '$RECEIVER_SERVICE_NAME' -n 50 --no-pager"

  echo "==> journalctl -u jukebox.service -n 50 --no-pager"
  ssh -p "$PI_PORT" "$SSH_TARGET" "journalctl -u jukebox.service -n 50 --no-pager"

  if print_receiver_visibility; then
    receiver_status_ok=1
  else
    receiver_status_ok=0
    overall_status=1
  fi
}

run_smoke_replay() {
  replay_status_ok=1
  if [ -z "$SMOKE_URI" ]; then
    return
  fi

  echo "==> One-shot stdin replay"
  replay_output=$(ssh -p "$PI_PORT" "$SSH_TARGET" /bin/sh <<EOF 2>&1
set -eu
cd '$PI_ROOT'
sudo /bin/sh <<'SH'
set -eu
set -a
. /etc/jukebox/jukebox.env
set +a
printf '%s\n' '$SMOKE_URI' | JUKEBOX_INPUT_BACKEND=stdin '$PI_ROOT/.venv/bin/python' -m jukebox
SH
EOF
)
  printf '%s\n' "$replay_output"

  case "$replay_output" in
    *"[PLAYBACK spotify] started"*)
      replay_status_ok=1
      ;;
    *"[PLAYBACK spotify] failed: spotify_api_auth_error"*)
      replay_status_ok=0
      overall_status=1
      ;;
    *"[PLAYBACK spotify] failed: device_not_listed"*)
      replay_status_ok=0
      overall_status=1
      ;;
    *"[PLAYBACK spotify] failed: connect_transfer_failed"*)
      replay_status_ok=0
      overall_status=1
      ;;
    *"[PLAYBACK spotify] failed: network_discovery_failed"*)
      replay_status_ok=0
      overall_status=1
      ;;
    *)
      replay_status_ok=0
      overall_status=1
      ;;
  esac

  if [ "$replay_status_ok" -ne 1 ]; then
    echo "Smoke replay did not reach a playback-start event." >&2
  fi
}

run_smoke_iteration() {
  print_remote_state
  run_smoke_replay
}

run_smoke_iteration

if [ "$SMOKE_REBOOT" != "1" ]; then
  exit "$overall_status"
fi

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
