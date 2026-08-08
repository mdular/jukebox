# Spotify API Discipline

## Purpose

EPIC 4 treats Spotify API discipline as a reliability requirement, not an optimization.
Ordinary idle operation must not consume enough Spotify API budget to interfere with scan-time playback on the jukebox target.

## Rules

- `status()` is a passive cached read only.
- `player_active()` is a passive cached read only.
- `current_player_active()` is the only allowed scan-scoped live player-state read.
- Health monitoring must never trigger Spotify API calls.
- Idle monitoring must never trigger Spotify API calls.
- `status.json` generation must never trigger Spotify API calls.
- OAuth token refreshes must be cached and reused until they expire.
- Startup probing is allowed to make live Spotify calls, but only during the bounded startup window.

## Allowed Live Call Surfaces

- `probe()`
  - refresh controller auth if needed
  - seed passive playback status
  - perform bounded target-device visibility retries during startup
- `dispatch()`
  - refresh token if needed
  - resolve target device
  - start playback using direct-play-first handoff with transfer fallback
  - confirm playback on the configured target
- `enqueue()`
  - resolve target device
  - queue one track
- `stop()`
  - resolve target device
  - pause playback
- `skip_next()`
  - resolve target device
  - advance playback
- `set_volume_percent()`
  - resolve target device
  - apply a volume preset
- `current_player_active()`
  - perform one live `/v1/me/player` read on the scan path only

## Passive Surfaces

- `status()`
- `player_active()`
- `RuntimeHealthMonitor`
- `IdleMonitor`
- `OperatorHttpServer` runtime status and `status.json`
- terminal degraded-state rendering
- structured degraded-state logging

These surfaces must read cached state only. They are not allowed to refresh tokens, resolve devices, or poll Spotify player state.

## Cache Expectations

- `probe()` seeds the passive playback cache before the runtime starts serving health and operator status.
- Successful playback operations update cached playback status and cached player activity as side effects.
- Degraded playback operations update cached degraded status so operator feedback stays honest without adding background polling.
- `current_player_active()` may refresh the cached current-activity view because it is part of a user scan path, not a background observer.

## Health Polling

- `JUKEBOX_HEALTH_POLL_INTERVAL_SECONDS` defaults to `15.0`.
- The slower default is intentional even after passive-status adoption; it keeps state churn and log churn lower on Raspberry Pi 3.
- Reducing the poll interval should not affect Spotify API pressure once the passive-status rules above are respected, but the default should remain conservative.

## Failure Visibility

- Spotify throttling must surface as `spotify_rate_limited`, not as generic network failure.
- If Spotify returns `Retry-After`, surface it in the degraded message for operators.
- Distinct degraded states matter because the runtime is intentionally not using background recovery polling to resolve them.

## Queue-Mode Exception

Queue mode needs one exception to the passive-status rule:

- `current_player_active()` may perform a scan-scoped live read to decide whether a track should queue or fall back to replace-style dispatch.

This exception exists because a passive cached `player_active()` value can be stale and can silently misroute a child’s scan.
The exception is limited to the scan path so the runtime preserves zero background Spotify API polling.
