#!/bin/sh
set -eu

command_name=${1:-}

STATE_DIR=${JUKEBOX_WIFI_HELPER_STATE_DIR:-/var/lib/jukebox/wifi-helper}
PENDING_FILE=$STATE_DIR/pending-trial.env
BOOT_ID_FILE=${JUKEBOX_WIFI_BOOT_ID_FILE:-/proc/sys/kernel/random/boot_id}
NMCLI_COMMAND=${JUKEBOX_WIFI_NMCLI_COMMAND:-nmcli}
WIFI_INTERFACE=${JUKEBOX_WIFI_INTERFACE:-}
SETUP_AP_CONNECTION_NAME=${JUKEBOX_WIFI_AP_CONNECTION_NAME:-jukebox-setup-ap}
CLIENT_CONNECTION_PREFIX=${JUKEBOX_WIFI_CLIENT_CONNECTION_PREFIX:-jukebox-client}
ROLLBACK_TIMEOUT_SECONDS=${JUKEBOX_WIFI_ROLLBACK_TIMEOUT_SECONDS:-120}
DISABLE_BACKGROUND=${JUKEBOX_WIFI_HELPER_DISABLE_BACKGROUND:-0}
SETUP_AP_SSID=${JUKEBOX_SETUP_AP_SSID:-}
SETUP_AP_PASSPHRASE=${JUKEBOX_SETUP_AP_PASSPHRASE:-}

emit_json() {
  printf '%s\n' "$1"
}

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

ensure_state_dir() {
  mkdir -p "$STATE_DIR"
}

shell_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

write_pending() {
  previous_connection_name=$1
  trial_connection_name=$2
  deadline_epoch=$3
  boot_id=$4

  ensure_state_dir
  : >"$PENDING_FILE"
  printf 'PREVIOUS_CONNECTION_NAME=%s\n' "$(shell_quote "$previous_connection_name")" >>"$PENDING_FILE"
  printf 'TRIAL_CONNECTION_NAME=%s\n' "$(shell_quote "$trial_connection_name")" >>"$PENDING_FILE"
  printf 'DEADLINE_EPOCH=%s\n' "$(shell_quote "$deadline_epoch")" >>"$PENDING_FILE"
  printf 'PENDING_BOOT_ID=%s\n' "$(shell_quote "$boot_id")" >>"$PENDING_FILE"
}

clear_pending() {
  rm -f "$PENDING_FILE"
}

load_pending() {
  if [ ! -f "$PENDING_FILE" ]; then
    return 1
  fi
  # shellcheck disable=SC1090
  . "$PENDING_FILE"
  return 0
}

current_boot_id() {
  if [ -f "$BOOT_ID_FILE" ]; then
    tr -d '\n' <"$BOOT_ID_FILE"
    return
  fi
  printf '%s' unknown
}

current_epoch() {
  date +%s
}

require_nmcli() {
  if [ ! -x "$NMCLI_COMMAND" ] && ! command -v "$NMCLI_COMMAND" >/dev/null 2>&1; then
    fail "nmcli is required for Wi-Fi helper operations."
  fi
}

wifi_interface() {
  if [ -n "$WIFI_INTERFACE" ]; then
    printf '%s\n' "$WIFI_INTERFACE"
    return
  fi

  device_lines=$("$NMCLI_COMMAND" -t -f DEVICE,TYPE,STATE device status 2>/dev/null || true)
  old_ifs=$IFS
  IFS='
'
  for line in $device_lines; do
    type_part=${line#*:}
    type=${type_part%%:*}
    device=${line%%:*}
    if [ "$type" = "wifi" ] && [ -n "$device" ]; then
      IFS=$old_ifs
      printf '%s\n' "$device"
      return
    fi
  done
  IFS=$old_ifs
  fail "No Wi-Fi interface found."
}

list_connection_lines() {
  "$NMCLI_COMMAND" -t -f TYPE,NAME connection show "$@"
}

active_wifi_connection_name() {
  active_lines=$(list_connection_lines --active 2>/dev/null || true)
  old_ifs=$IFS
  IFS='
'
  for line in $active_lines; do
    type=${line%%:*}
    name=${line#*:}
    if [ "$type" = "802-11-wireless" ] && [ -n "$name" ]; then
      IFS=$old_ifs
      printf '%s\n' "$name"
      return
    fi
  done
  IFS=$old_ifs
  printf '\n'
}

has_saved_client_config() {
  ignored_trial_name=
  if load_pending; then
    ignored_trial_name=$TRIAL_CONNECTION_NAME
  fi

  connection_lines=$(list_connection_lines 2>/dev/null || true)
  old_ifs=$IFS
  IFS='
'
  for line in $connection_lines; do
    type=${line%%:*}
    name=${line#*:}
    if [ "$type" != "802-11-wireless" ]; then
      continue
    fi
    if [ "$name" = "$SETUP_AP_CONNECTION_NAME" ]; then
      continue
    fi
    if [ -n "$ignored_trial_name" ] && [ "$name" = "$ignored_trial_name" ]; then
      continue
    fi
    IFS=$old_ifs
    return 0
  done
  IFS=$old_ifs
  return 1
}

client_connected() {
  active_name=$(active_wifi_connection_name)
  [ -n "$active_name" ] && [ "$active_name" != "$SETUP_AP_CONNECTION_NAME" ]
}

ap_active() {
  active_name=$(active_wifi_connection_name)
  [ "$active_name" = "$SETUP_AP_CONNECTION_NAME" ]
}

delete_connection_if_present() {
  connection_name=$1
  if [ -z "$connection_name" ]; then
    return
  fi
  if list_connection_lines 2>/dev/null | grep -F ":$connection_name" >/dev/null 2>&1; then
    "$NMCLI_COMMAND" connection delete id "$connection_name" >/dev/null 2>&1 || true
  fi
}

disconnect_ap_if_active() {
  if ap_active; then
    "$NMCLI_COMMAND" connection down id "$SETUP_AP_CONNECTION_NAME" >/dev/null 2>&1 || true
  fi
}

rollback_pending() {
  if ! load_pending; then
    return 0
  fi

  disconnect_ap_if_active
  if [ -n "$TRIAL_CONNECTION_NAME" ] && [ "$TRIAL_CONNECTION_NAME" != "$PREVIOUS_CONNECTION_NAME" ]; then
    delete_connection_if_present "$TRIAL_CONNECTION_NAME"
  fi
  if [ -n "$PREVIOUS_CONNECTION_NAME" ]; then
    "$NMCLI_COMMAND" connection up id "$PREVIOUS_CONNECTION_NAME" ifname "$(wifi_interface)" >/dev/null
  fi
  clear_pending
  return 0
}

resolve_pending_trial() {
  if ! load_pending; then
    return 0
  fi

  current_id=$(current_boot_id)
  now=$(current_epoch)
  if [ "$current_id" != "$PENDING_BOOT_ID" ]; then
    rollback_pending
    return 0
  fi
  if [ "$now" -ge "$DEADLINE_EPOCH" ]; then
    rollback_pending
    return 0
  fi
  return 0
}

arm_rollback_timer() {
  if [ ! -f "$PENDING_FILE" ]; then
    return
  fi
  if [ "$DISABLE_BACKGROUND" = "1" ]; then
    return
  fi
  if ! command -v nohup >/dev/null 2>&1; then
    return
  fi

  nohup /bin/sh -c "sleep $ROLLBACK_TIMEOUT_SECONDS && \"$0\" rollback-pending >/dev/null 2>&1" >/dev/null 2>&1 &
}

ensure_setup_ap_configured() {
  if [ -z "$SETUP_AP_SSID" ]; then
    fail "JUKEBOX_SETUP_AP_SSID must be configured for setup AP mode."
  fi
  if [ -n "$SETUP_AP_PASSPHRASE" ] && [ "${#SETUP_AP_PASSPHRASE}" -lt 8 ]; then
    fail "JUKEBOX_SETUP_AP_PASSPHRASE must be at least 8 characters."
  fi
}

sanitize_connection_name() {
  value=$1
  sanitized=$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-')
  sanitized=${sanitized#-}
  sanitized=${sanitized%-}
  if [ -z "$sanitized" ]; then
    sanitized=client
  fi
  printf '%s-%s\n' "$CLIENT_CONNECTION_PREFIX" "$sanitized"
}

start_ap_connection() {
  ensure_setup_ap_configured
  iface=$(wifi_interface)
  if [ -n "$SETUP_AP_PASSPHRASE" ]; then
    "$NMCLI_COMMAND" device wifi hotspot \
      ifname "$iface" \
      con-name "$SETUP_AP_CONNECTION_NAME" \
      ssid "$SETUP_AP_SSID" \
      password "$SETUP_AP_PASSPHRASE" >/dev/null
  else
    "$NMCLI_COMMAND" device wifi hotspot \
      ifname "$iface" \
      con-name "$SETUP_AP_CONNECTION_NAME" \
      ssid "$SETUP_AP_SSID" >/dev/null
  fi
}

reset_client_cmd() {
  require_nmcli
  resolve_pending_trial

  previous_connection_name=
  if client_connected; then
    previous_connection_name=$(active_wifi_connection_name)
    deadline_epoch=$(( $(current_epoch) + ROLLBACK_TIMEOUT_SECONDS ))
    write_pending "$previous_connection_name" "" "$deadline_epoch" "$(current_boot_id)"
    arm_rollback_timer
  else
    clear_pending
  fi

  start_ap_connection
  printf '%s\n' "setup ap started"
}

start_ap_cmd() {
  require_nmcli
  resolve_pending_trial
  clear_pending
  start_ap_connection
  printf '%s\n' "setup ap started"
}

apply_client_cmd() {
  require_nmcli
  resolve_pending_trial

  ssid=${1:-}
  passphrase=${2:-}
  if [ -z "$ssid" ]; then
    fail "usage: $0 apply-client <ssid> <passphrase>"
  fi

  previous_connection_name=
  if load_pending; then
    previous_connection_name=$PREVIOUS_CONNECTION_NAME
  elif client_connected; then
    previous_connection_name=$(active_wifi_connection_name)
  fi

  trial_connection_name=$(sanitize_connection_name "$ssid")
  deadline_epoch=$(( $(current_epoch) + ROLLBACK_TIMEOUT_SECONDS ))

  if [ -n "$previous_connection_name" ] || ap_active; then
    write_pending "$previous_connection_name" "$trial_connection_name" "$deadline_epoch" "$(current_boot_id)"
    arm_rollback_timer
  fi

  delete_connection_if_present "$trial_connection_name"
  iface=$(wifi_interface)
  if [ -n "$passphrase" ]; then
    "$NMCLI_COMMAND" device wifi connect "$ssid" password "$passphrase" ifname "$iface" name "$trial_connection_name" >/dev/null
  else
    "$NMCLI_COMMAND" device wifi connect "$ssid" ifname "$iface" name "$trial_connection_name" >/dev/null
  fi

  disconnect_ap_if_active
  if [ -n "$previous_connection_name" ] && [ "$previous_connection_name" != "$trial_connection_name" ]; then
    delete_connection_if_present "$previous_connection_name"
  fi
  clear_pending

  emit_json '{"message":"wifi settings applied"}'
}

status_cmd() {
  require_nmcli
  resolve_pending_trial

  has_client_config=false
  client_connected_flag=false
  ap_active_flag=false

  if has_saved_client_config; then
    has_client_config=true
  fi
  if client_connected; then
    client_connected_flag=true
  fi
  if ap_active; then
    ap_active_flag=true
  fi

  emit_json "{\"has_client_config\": $has_client_config, \"client_connected\": $client_connected_flag, \"ap_active\": $ap_active_flag}"
}

case "$command_name" in
  status)
    status_cmd
    ;;
  start-ap)
    start_ap_cmd
    ;;
  apply-client)
    apply_client_cmd "${2:-}" "${3:-}"
    ;;
  reset-client)
    reset_client_cmd
    ;;
  rollback-pending)
    require_nmcli
    rollback_pending
    ;;
  *)
    printf '%s\n' "usage: $0 {status|start-ap|apply-client|reset-client|rollback-pending}" >&2
    exit 2
    ;;
esac
