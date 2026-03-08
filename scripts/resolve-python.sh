#!/bin/sh
set -eu

print_guidance() {
  printf '%s\n' 'Jukebox requires Python 3.11+.' >&2
  printf '%s\n' 'Install a supported interpreter and rerun with PYTHON=/path/to/python3.11 make venv' >&2
}

is_runnable() {
  [ -x "$1" ] || command -v "$1" >/dev/null 2>&1
}

supports_python() {
  "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1
}

resolve_explicit_python() {
  candidate=$1

  if ! is_runnable "$candidate"; then
    printf "Configured Python interpreter '%s' was not found.\n" "$candidate" >&2
    print_guidance
    exit 1
  fi

  if supports_python "$candidate"; then
    printf '%s\n' "$candidate"
    exit 0
  fi

  version=$("$candidate" --version 2>&1 || printf '%s' 'unknown version')
  printf "Configured Python interpreter '%s' is unsupported (%s).\n" "$candidate" "$version" >&2
  print_guidance
  exit 1
}

if [ -n "${PYTHON:-}" ]; then
  resolve_explicit_python "$PYTHON"
fi

for candidate in python3.13 python3.12 python3.11 python3 python; do
  if is_runnable "$candidate" && supports_python "$candidate"; then
    printf '%s\n' "$candidate"
    exit 0
  fi
done

printf '%s\n' 'No supported Python interpreter was found on PATH.' >&2
print_guidance
exit 1
