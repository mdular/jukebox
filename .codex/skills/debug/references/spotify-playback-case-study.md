# Spotify Playback Case Study

This reference captures the debugging pattern from the March-April 2026 Spotify playback investigations.

## What The Successful Workflow Did Right

### Read the whole control path

- It read `playback_spotify.py` end to end instead of sampling method names.
- It traced `dispatch()` as an ordered flow, not as isolated helpers.
- It checked controller entrypoints to confirm replace mode was not hiding extra context-reset logic.
- It verified dead helpers by checking call sites instead of assuming intent from unused code.

### Run tests before editing

- Existing tests were already failing before the successful patch.
- That exposed drift between the tests and the checked-in implementation.
- This prevented a false fix where the code would have been bent back toward stale test expectations.

### Follow raw API evidence

- The workflow looked at real Spotify responses during validation.
- That surfaced a second major issue family: throttling, token churn, and API-budget pressure.
- The later `spotify_rate_limited` and `Retry-After` work came from following evidence, not from random scope creep.

### Keep the fix small once the theory is supported

- The handoff fix was narrow: direct play first, transfer only as fallback.
- Dead album-context helpers and stale tests were removed instead of defended.
- Extra hardening only became justified after new evidence appeared.

## What This Means For Future Sessions

- Do not call an adjacent discovery accidental when it came from inspecting real responses.
- Treat hidden 429s as first-class evidence because they can distort both behavior and diagnosis.
- Distinguish code facts from branch intent and from UI anecdotes.
- Preserve reproduction tooling early when a bug depends on Spotify Connect state.

