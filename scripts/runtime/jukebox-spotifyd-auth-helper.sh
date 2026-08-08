#!/bin/sh
set -eu

command_name=${1:-}

STATE_DIR=${JUKEBOX_SPOTIFYD_AUTH_HELPER_STATE_DIR:-/var/lib/jukebox/spotifyd-auth-helper}
STATE_FILE=$STATE_DIR/state.json
LOG_FILE=$STATE_DIR/spotifyd-auth.log
SPOTIFYD_COMMAND=${JUKEBOX_SPOTIFYD_AUTH_COMMAND:-spotifyd}

emit_json() {
  printf '%s\n' "$1"
}

ensure_state_dir() {
  mkdir -p "$STATE_DIR"
}

json_escape() {
  printf '%s' "$1" | tr '\n' ' ' | sed 's/\\/\\\\/g; s/"/\\"/g'
}

state_json() {
  state=$1
  message=$2
  printf '{"state":"%s","message":"%s"}' "$state" "$(json_escape "$message")"
}

write_state() {
  state=$1
  message=$2

  ensure_state_dir
  tmp_file=$STATE_FILE.tmp
  json_payload=$(state_json "$state" "$message")
  printf '%s\n' "$json_payload" >"$tmp_file"
  mv "$tmp_file" "$STATE_FILE"
}

emit_state() {
  if [ ! -f "$STATE_FILE" ]; then
    emit_json "$(state_json failed "receiver authentication has not started")"
    return
  fi

  state=$(sed -n 's/.*"state":"\([^"]*\)".*/\1/p' "$STATE_FILE")
  message=$(sed -n 's/.*"message":"\([^"]*\)".*/\1/p' "$STATE_FILE" | sed 's/\\"/"/g; s/\\\\/\\/g')
  approval_url=$(approval_url_from_log)
  if [ -n "$approval_url" ]; then
    emit_json "{\"state\":\"$state\",\"message\":\"$(json_escape "$message")\",\"approval_url\":\"$(json_escape "$approval_url")\"}"
    return
  fi
  emit_json "$(state_json "$state" "$message")"
}

current_state() {
  if [ ! -f "$STATE_FILE" ]; then
    printf '%s\n' failed
    return
  fi

  state=$(sed -n 's/.*"state":"\([^"]*\)".*/\1/p' "$STATE_FILE")
  if [ -z "$state" ]; then
    printf '%s\n' failed
    return
  fi
  printf '%s\n' "$state"
}

spotifyd_available() {
  if [ -x "$SPOTIFYD_COMMAND" ]; then
    return 0
  fi
  command -v "$SPOTIFYD_COMMAND" >/dev/null 2>&1
}

launch_worker() {
  if command -v nohup >/dev/null 2>&1; then
    nohup /bin/sh "$0" run-worker >/dev/null 2>&1 &
    return
  fi
  /bin/sh "$0" run-worker >/dev/null 2>&1 &
}

read_log_output() {
  if [ ! -f "$LOG_FILE" ]; then
    return
  fi
  tr '\n' ' ' <"$LOG_FILE" | sed 's/[[:space:]][[:space:]]*/ /g; s/^ //; s/ $//'
}

approval_url_from_log() {
  if [ ! -f "$LOG_FILE" ]; then
    return
  fi
  sed -n 's/.*\(https\{0,1\}:\/\/[^[:space:]]*\).*/\1/p' "$LOG_FILE" | head -n 1
}

start_cmd() {
  ensure_state_dir

  if ! spotifyd_available; then
    write_state failed "spotifyd is not installed or not on PATH"
    emit_state
    return
  fi

  state=$(current_state)
  if [ "$state" = "pending" ] || [ "$state" = "running" ]; then
    emit_state
    return
  fi

  : >"$LOG_FILE"
  write_state pending "starting receiver authentication"
  launch_worker
  emit_state
}

status_cmd() {
  emit_state
}

run_worker_cmd() {
  if ! spotifyd_available; then
    write_state failed "spotifyd is not installed or not on PATH"
    return
  fi

  write_state running "waiting for Spotify approval"
  if "$SPOTIFYD_COMMAND" authenticate >"$LOG_FILE" 2>&1; then
    write_state succeeded "receiver authentication completed"
    return
  fi

  output=$(read_log_output)
  if [ -z "$output" ]; then
    output="spotifyd authenticate failed"
  fi
  write_state failed "$output"
}

case "$command_name" in
  start)
    start_cmd
    ;;
  status)
    status_cmd
    ;;
  run-worker)
    run_worker_cmd
    ;;
  *)
    printf '%s\n' "usage: $0 {start|status}" >&2
    exit 2
    ;;
esac
