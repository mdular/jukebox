# Spotify API Checklist

Load this reference for Spotify playback, boot-readiness, or rate-limit incidents.

## Sequence To Read

1. Controller entrypoint and playback mode handling.
2. `dispatch()` or equivalent end-to-end control flow.
3. Token refresh path.
4. Device lookup path.
5. Transfer or direct-play path.
6. Playback confirmation path.
7. Background status, idle, or health paths that may consume API budget.

## Evidence To Capture

- Request order.
- Endpoint used.
- Query parameters and JSON payload shape.
- Response status code.
- Response body fields that matter.
- Headers that matter, especially `Retry-After`.
- Whether the device was audible, merely visible, or not visible at all.

## Endpoint Questions

### Token refresh

- Is the code refreshing on every control or status read?
- Are repeated refreshes creating avoidable 429 pressure?
- Does a 429 on auth refresh explain later control-path failures?

### `/v1/me/player/devices`

- Is the target device missing, renamed, or merely delayed after boot?
- Is the code assuming a stale device ID instead of resolving current visibility?

### `/v1/me/player`

- Is playback already active on another context?
- Is device state current, stale, or absent?
- Does confirmation logic treat any target-device playback as success even when item metadata never matches?

### `/v1/me/player` transfer

- Is transfer happening before direct play?
- Could transfer revive stale session state onto the receiver?

### `/v1/me/player/play`

- Is the request using `{"uris": [...]}` or `{"context_uri": ...}`?
- Is the payload shape actually used by the code, or only by dead helpers and stale tests?
- Does the endpoint already accept `device_id`, making a prior transfer unnecessary in the happy path?

## Cross-Cutting Checks

- Count background calls from health, idle, and status code paths.
- Treat `429` as a major competing explanation, not just noisy validation output.
- Compare client UI with actual audible behavior before concluding playback is wrong.
- If tests expect one payload shape and the code sends another, decide whether the tests drifted or the implementation regressed before editing anything.
