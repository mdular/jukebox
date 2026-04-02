#!/bin/sh
set -eu

command_name=${1:-}

emit_json() {
  printf '%s\n' "$1"
}

status_cmd() {
  has_client_config=false
  client_connected=false
  ap_active=false

  if [ -f /etc/wpa_supplicant/wpa_supplicant.conf ]; then
    has_client_config=true
  fi
  if command -v find >/dev/null 2>&1 && [ -d /etc/NetworkManager/system-connections ]; then
    if find /etc/NetworkManager/system-connections -name '*.nmconnection' -print -quit | grep -q .; then
      has_client_config=true
    fi
  fi
  if command -v iwgetid >/dev/null 2>&1 && [ -n "$(iwgetid -r 2>/dev/null || true)" ]; then
    client_connected=true
  fi

  emit_json "{\"has_client_config\": $has_client_config, \"client_connected\": $client_connected, \"ap_active\": $ap_active}"
}

unsupported() {
  printf '%s\n' "wifi helper action '$1' is not automated by this repo yet; implement host-specific networking here." >&2
  exit 1
}

case "$command_name" in
  status)
    status_cmd
    ;;
  start-ap)
    unsupported start-ap
    ;;
  apply-client)
    unsupported apply-client
    ;;
  reset-client)
    unsupported reset-client
    ;;
  *)
    printf '%s\n' "usage: $0 {status|start-ap|apply-client|reset-client}" >&2
    exit 2
    ;;
esac
