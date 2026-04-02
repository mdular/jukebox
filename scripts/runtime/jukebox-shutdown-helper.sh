#!/bin/sh
set -eu

reason=${2:-unknown}

if [ "${1:-}" != "--reason" ]; then
  printf '%s\n' "usage: $0 --reason <action|idle>" >&2
  exit 2
fi

printf '%s\n' "shutdown requested: $reason"
exec /sbin/shutdown -h now "jukebox: $reason"
