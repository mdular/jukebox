#!/bin/sh
set -eu

command_name=${1:-}

case "$command_name" in
  start)
    if ! command -v spotifyd >/dev/null 2>&1; then
      printf '%s\n' '{"state":"failed","message":"spotifyd is not installed or not on PATH"}'
      exit 1
    fi
    printf '%s\n' '{"state":"failed","message":"interactive spotifyd authenticate wrapping must be completed on the Pi host before production use"}'
    exit 1
    ;;
  status)
    printf '%s\n' '{"state":"unknown","message":"no active auth session"}'
    ;;
  *)
    printf '%s\n' "usage: $0 {start|status}" >&2
    exit 2
    ;;
esac
