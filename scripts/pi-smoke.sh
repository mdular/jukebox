#!/bin/sh
set -eu

PI_HOST=${JUKEBOX_PI_HOST:?Set JUKEBOX_PI_HOST to the Raspberry Pi hostname or IP.}
PI_USER=${JUKEBOX_PI_USER:-pi}
PI_PORT=${JUKEBOX_PI_PORT:-22}
PI_ROOT=${JUKEBOX_PI_ROOT:-/opt/jukebox}
SMOKE_URI=${JUKEBOX_SMOKE_URI:-}
SMOKE_REBOOT=${JUKEBOX_SMOKE_REBOOT:-0}

SSH_TARGET=$PI_USER@$PI_HOST

print_unit_state() {
  unit_name=$1

  echo "==> systemctl is-active $unit_name"
  unit_state=$(ssh -p "$PI_PORT" "$SSH_TARGET" "systemctl is-active '$unit_name'" || true)
  printf '%s\n' "$unit_state"
}

print_remote_state() {
  print_unit_state raspotify.service
  print_unit_state jukebox.service

  echo "==> journalctl -u raspotify.service -n 50 --no-pager"
  ssh -p "$PI_PORT" "$SSH_TARGET" "journalctl -u raspotify.service -n 50 --no-pager"

  echo "==> journalctl -u jukebox.service -n 50 --no-pager"
  ssh -p "$PI_PORT" "$SSH_TARGET" "journalctl -u jukebox.service -n 50 --no-pager"

  echo "==> Spotify Web API /me/player/devices snapshot"
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

required = (
    "JUKEBOX_SPOTIFY_CLIENT_ID",
    "JUKEBOX_SPOTIFY_CLIENT_SECRET",
    "JUKEBOX_SPOTIFY_REFRESH_TOKEN",
)
missing = [key for key in required if not os.environ.get(key)]
if missing:
    print("missing env: " + ", ".join(missing), file=sys.stderr)
    raise SystemExit(1)

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
    print("token refresh failed with HTTP {code}".format(code=exc.code), file=sys.stderr)
    raise
except URLError as exc:
    print("token refresh transport error: {reason}".format(reason=exc.reason), file=sys.stderr)
    raise

access_token = token_payload.get("access_token")
if not isinstance(access_token, str) or access_token == "":
    print("token refresh response did not include an access token", file=sys.stderr)
    raise SystemExit(1)

devices_request = Request(
    "https://api.spotify.com/v1/me/player/devices",
    headers={"Authorization": "Bearer " + access_token},
    method="GET",
)

try:
    with urlopen(devices_request, timeout=5) as response:
        devices_payload = json.loads(response.read().decode("utf-8"))
except HTTPError as exc:
    print("devices request failed with HTTP {code}".format(code=exc.code), file=sys.stderr)
    raise
except URLError as exc:
    print("devices request transport error: {reason}".format(reason=exc.reason), file=sys.stderr)
    raise

devices = devices_payload.get("devices")
if isinstance(devices, list):
    target_name = os.environ.get("JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME")
    print(
        json.dumps(
            {
                "device_count": len(devices),
                "target_device_name": target_name,
                "target_visible": any(
                    isinstance(device, dict) and device.get("name") == target_name
                    for device in devices
                )
                if target_name
                else None,
                "devices": devices,
            },
            indent=2,
            sort_keys=True,
        )
    )
else:
    print(json.dumps(devices_payload, indent=2, sort_keys=True))
PY
SH
EOF
}

print_remote_state

if [ -n "$SMOKE_URI" ]; then
  echo "==> One-shot stdin replay"
  ssh -p "$PI_PORT" "$SSH_TARGET" /bin/sh <<EOF
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
fi

if [ "$SMOKE_REBOOT" != "1" ]; then
  exit 0
fi

ssh -p "$PI_PORT" "$SSH_TARGET" "sudo reboot" || true
sleep 5

while ! ssh -p "$PI_PORT" -o ConnectTimeout=5 "$SSH_TARGET" "true" >/dev/null 2>&1; do
  sleep 5
done

print_remote_state
