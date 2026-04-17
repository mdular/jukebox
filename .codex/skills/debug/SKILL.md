---
name: debug
description: Evidence-first debugging workflow for the QR Card Jukebox repo. Use when a bug is unclear, previous fixes failed, tests and live behavior disagree, or Spotify, Pi, scanner, logging, or startup-readiness issues may be hiding the real failure behind stale state, rate limiting, or misleading client UI.
---

# Debug

Use this skill to stop guess-driven debugging. Reconstruct the real control path, inspect runtime evidence, and only then decide whether the bug is in the code, the tests, the docs, the environment, or the current theory.

## First Pass

- Restate the symptom as observations, not conclusions.
- Name the entrypoints and downstream modules likely involved.
- Read the full control path end to end before trusting grep hits, method names, or test names.
- Run existing validation before edits. In this repo prefer `.venv/bin/pytest`, `.venv/bin/python`, or `make` targets from `AGENTS.md`.
- If tests already fail before edits, treat that as drift evidence. Decide whether the tests are stale, the code is wrong, or both.

## Evidence Rules

- Separate `observation`, `code fact`, `API evidence`, `interpretation`, and `unknown`.
- Prefer raw responses, status codes, bodies, and relevant headers over anecdotes from clients.
- Do not ignore adjacent failures that surface during diagnosis. A second issue exposed by real evidence may be the dominant problem.
- Do not trust UI state alone when Spotify or another external system can lag, cache, or lie.
- Raise the bar before adding runtime complexity. State the exact failing scenario the extra logic would fix.

## Workflow

1. Capture the current symptom, environment, and exact failure statement.
2. Read the whole code path that can produce the behavior.
3. Run the nearest tests or checks before editing.
4. Compare the failing behavior with the implementation, not with assumptions about how the code was supposed to work.
5. Inspect raw runtime evidence. For HTTP-backed issues, check request ordering, status codes, response bodies, and headers.
6. Keep at least two live hypotheses until one is contradicted by evidence.
7. Implement the smallest fix that matches the best-supported hypothesis.
8. Re-run validation and record any adjacent issue uncovered during the run.
9. Leave a carry-forward note with proven facts, remaining unknowns, and any reproduction tooling created.

## Spotify And Pi Focus

- Read [references/spotify-api-checklist.md](references/spotify-api-checklist.md) for Spotify playback, startup, or rate-limit incidents.
- Read [references/spotify-playback-case-study.md](references/spotify-playback-case-study.md) when the failure resembles the March-April 2026 playback, boot, or 429 investigations.
- Watch for `429`, `Retry-After`, token refresh frequency, background polling, `device_not_listed`, stale client metadata, and mismatches between audible behavior and client UI.
- Distinguish payload-shape questions from session-state questions. `{"uris": [...]}` versus `{"context_uri": ...}` is not the same as transfer ordering or stale-context behavior.
- Preserve or create reproduction tooling early once a bug depends on external device or API state.

## Output Contract

- Problem statement
- Code path read
- Evidence table
- Competing hypotheses
- Chosen fix or next measurement
- Validation run
- Remaining unknowns

## Escalation

- If multiple sessions or branches already disagree on the diagnosis, invoke `$workflow-retro` before committing to another fix path.
- If live Pi behavior contradicts docs, treat doc drift as part of the debugging task, not as cleanup after the fix.
