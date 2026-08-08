# Spotify Connect Debug Runbook

## Purpose

Use this runbook when the jukebox target appears to accept a scan but does not reliably take over playback, starts on the wrong client, or reports degraded Spotify states such as `receiver_unavailable` or `spotify_rate_limited`.

This runbook matches the EPIC 4 baseline:

- direct-play-first handoff with transfer fallback
- single-URI track starts for replace mode
- passive cached runtime status for health, idle, and `status.json`
- scan-scoped `current_player_active()` only for queue-mode track routing

## Before You Start

- Use the real runtime env file on the Pi or export the same Spotify controller credentials locally.
- Confirm these env vars are set:
  - `JUKEBOX_SPOTIFY_CLIENT_ID`
  - `JUKEBOX_SPOTIFY_CLIENT_SECRET`
  - `JUKEBOX_SPOTIFY_REFRESH_TOKEN`
  - `JUKEBOX_SPOTIFY_DEVICE_ID` or `JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME`
- Keep the target receiver running while probing.

## Fast Checks

1. Check the operator status surface:

```sh
curl -s http://127.0.0.1:${JUKEBOX_OPERATOR_HTTP_PORT:-8080}/status.json | python3 -m json.tool
```

Focus on:

- `runtime.playback.code`
- `runtime.playback.reason_code`
- `runtime.playback.device_name`
- `feedback.display_state`

2. Check recent service logs:

```sh
sudo journalctl -u jukebox.service -n 100 --no-pager
sudo journalctl -u spotifyd.service -n 100 --no-pager
```

Look for:

- `spotify_rate_limited`
- `receiver_unavailable`
- controller-auth failures
- playback success lines that do not match what you heard

## Probe Script

Use the dedicated probe script to test one URI against the configured target without relying on the controller loop:

```sh
.venv/bin/python scripts/spotify_connect_probe.py spotify:track:6rqhFgbbKwnb9MLmUQDhG6
```

The script prints JSON with:

- the configured target device
- preflight `/me/player` state
- the direct play attempt
- the transfer fallback attempt, if needed
- the retry play attempt, if needed
- post-play `/me/player` state

## How To Read The Output

- `direct_play.ok = true`
  - direct play succeeded without needing transfer
- `direct_play.ok = false` and `transfer.ok = true`
  - direct play did not take immediately; explicit transfer was needed
- `post_play.json.device.id` does not match the configured target
  - another Spotify client still owns playback
- `post_play.json` is `null`
  - Spotify still reports no active player after the attempt
- `result = failed`
  - handoff did not succeed even after the fallback path

## Reproduction Matrix

Run at least these cases before changing backend behavior:

1. Target already visible and idle, replace-mode track
2. Another Spotify client currently active elsewhere, replace-mode track
3. Queue mode with another client active elsewhere, first track scan
4. Queue mode with the jukebox already playing, later track scan
5. Cold boot while the receiver is still becoming visible

## Rate-Limit Handling

If the runtime or probe surfaces `spotify_rate_limited`:

- do not add more background polling
- record the `Retry-After` value if present
- wait for that window before repeating probes
- prefer one deliberate probe over repeated ad hoc scans

This matters because EPIC 4 explicitly treats avoidable Spotify API pressure as a reliability bug.

## What Not To Do

- Do not judge health, idle, or `status.json` behavior by adding live Spotify polling to those paths.
- Do not add snapshot-confirmation or completion-time logic unless you can reproduce a merge-target bug that the simpler EPIC 4 baseline fails to handle.
- Do not assume success on another client is equivalent to success on the jukebox target.
