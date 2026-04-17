# Spotify Playback Fix Retro and Post-Mortem

This retro compares the Spotify playback fix history across `main`, `playback-fix-codex`, and `fix-glitch-kilo-opus`.
It now serves two purposes:

- a retro across branches, sessions, and code paths
- a post-mortem on what was strongly evidenced, what was only hypothesized, and where the team over-inferred

It treats two linked threads as one story:

- the Spotify Connect handoff or stale-context playback glitch as the primary user-facing problem
- the later background-polling or rate-limit regression as the reliability problem that changed the direction of the newest branch

## Scope And Sources

This document uses the repository history as the source of truth.
It compares only:

- `main`
- `playback-fix-codex`
- `fix-glitch-kilo-opus`

It anchors the analysis in:

- `src/jukebox/adapters/playback_spotify.py`
- `src/jukebox/config.py`
- `src/jukebox/runtime.py`
- `src/jukebox/idle_monitor.py`
- `src/jukebox/runtime_health.py`
- `src/jukebox/core/controller.py`
- `docs/api-discipline.md`

Branch-only artifacts are called out explicitly when they matter:

- `playback-fix-codex` added `docs/spotify-connect-debug.md`
- `playback-fix-codex` added `scripts/spotify_connect_probe.py`

Those files do not exist on the current branch at the time of this retro, so they are referenced by branch name and commit rather than as live workspace files.

Anything not preserved in commit history is treated as unknown.
Any interpretation about session behavior, tooling, or model workflow is labeled as an inference.

This retro also uses two supplemental workflow inputs outside repo history:

- a later written explanation from the successful Kilo Code plus Opus 4.6 fix session
- public Kilo documentation describing the built-in `debug` agent as systematic troubleshooting with full tool access

Those inputs are used only to describe workflow shape and open questions.
They do not override repository history for code facts.
Exact hidden instructions, automatic context loading, and the relative contribution of Kilo tooling versus model differences remain unknown unless explicitly published.

## Evidence And Confidence Model

This document now grades major conclusions by evidence strength.
That is part of the learning from this incident: retrospective work must distinguish code facts from root-cause theories.

Confidence scale used here:

- `A`: directly supported by current code, commit history, tests, or validation logs
- `B`: strong inference from code and observed runtime behavior, but not fully proven
- `C`: plausible hypothesis with some support, but still meaningfully unconfirmed
- `D`: weak hypothesis or open speculation

Every major conclusion should be treated as one of these:

- proven by code history
- likely but not proven
- worth testing
- not justified yet

Assumption testing is now part of the retro and post-mortem process.
For each meaningful claim, the team should ask:

- what evidence actually supports this claim
- what evidence contradicts it
- what specific test would falsify it
- what complexity would we add if we treated it as true too early

## Timeline

### 2026-03-08 `8cd8ce6` on `main`

`probe()` stopped requiring receiver visibility and only validated Spotify auth.

Effect:

- fixed boot restart loops when Spotify reported zero devices after reboot
- moved receiver visibility from startup readiness into dispatch-time handling

### 2026-03-09 `309da1a` on `main`

EPIC 3 hardening added degraded runtime health and live `status()` checks against Spotify.

Effect:

- improved observability
- introduced a design where health supervision depended on fresh Spotify Web API reads

### 2026-04-02 `4b492a8` on `main`

EPIC 4 expanded the Spotify playback surface with:

- `enqueue()`
- `stop()`
- `skip_next()`
- `set_volume_percent()`

Effect:

- widened the playback adapter's responsibilities
- kept the live-status model in place

### 2026-04-03 `2238413` on `main`

`player_active()` and `IdleMonitor` were added.

Effect:

- idle checking began depending on live Spotify polling
- background activity now queried Spotify even without user scans

### 2026-04-03 `fb8d3c6` on `main`

Playback confirmation was loosened so "target device is playing" could count as success even when Spotify metadata was stale.

Effect:

- made the system more tolerant of delayed metadata
- also increased the chance of false-positive confirmation when the target was still playing old content

### 2026-04-13 `5fca785` on `playback-fix-codex`

Added prestart playback snapshots and changed-state confirmation.

Effect:

- tried to distinguish "the target started something new" from "the target kept playing stale context"
- directly addressed the false-positive hole introduced by `fb8d3c6`

### 2026-04-13 `edb5ccc` on `playback-fix-codex`

Added:

- `PlaybackRequest.stop_after_track`
- track detail lookup
- stop-after-track monitoring and background worker logic

Effect:

- changed replace-mode track behavior to use a single-track payload
- widened scope beyond the handoff glitch into playback lifecycle control

### 2026-04-13 `f6329de` on `playback-fix-codex`

Changed dispatch to direct-play first with transfer fallback.
Also added:

- `docs/spotify-connect-debug.md`
- `scripts/spotify_connect_probe.py`

Effect:

- directly tested the hypothesis that explicit transfer was reviving stale Spotify context
- created the only preserved reproduction tooling in repo history

### 2026-04-13 `03a26e6` on `fix-glitch-kilo-opus`

Kept direct-play-first and simplified track playback to `{"uris": [track]}` for track starts.
Also added:

- OAuth token caching
- passive cached `status()`
- passive cached `player_active()`
- startup `probe()` seeding for status cache
- explicit `spotify_rate_limited` status and log handling
- `docs/api-discipline.md`

Effect:

- fixed a real `main` regression around background Spotify polling and token churn
- shifted the branch toward API-discipline and rate-limit containment
- did not preserve the snapshot safeguard or the probe tooling from `playback-fix-codex`

### 2026-04-13 working tree on `fix-glitch-kilo-opus`

Uncommitted changes on top of `03a26e6` initially added `Retry-After` parsing to 429 handling in `src/jukebox/adapters/playback_spotify.py` and matching tests in `tests/test_playback_spotify.py`.

Effect:

- continues the same rate-limit visibility track
- does not change the stale-context confirmation model

### 2026-04-16 to 2026-04-17 current worktree on `fix-glitch-kilo-opus`

The current uncommitted worktree came from a live-device prompt against `jukebox.local` after a boot on 2026-04-16.
The reported symptoms were:

- boot did not reach working mode on its own
- scans produced `receiver_unavailable` with `device_not_listed`
- manual activation from the phone's Spotify app was needed before listening
- the device should have reached `ready` autonomously after boot
- the scan event did not appear to be logged

The worktree currently adds:

- bounded boot-time device retries inside `SpotifyPlaybackBackend.probe()`
- two new settings wired through `src/jukebox/config.py` and `src/jukebox/runtime.py`:
  - `JUKEBOX_SPOTIFY_DEVICE_PROBE_RETRY_COUNT`
  - `JUKEBOX_SPOTIFY_DEVICE_PROBE_RETRY_INTERVAL_SECONDS`
- `Retry-After` parsing and message rendering for 429 responses
- README documentation for the new startup-probe retry settings

Effect:

- turns the startup probe into a bounded "wait for receiver visibility" window instead of a single immediate lookup
- directly targets the boot-autonomy symptom from the 2026-04-16 prompt
- stays consistent with `docs/api-discipline.md` because startup probe calls are still explicit startup work and remain bounded
- does not change stale-context confirmation behavior
- does not restore the branch-only probe tooling from `playback-fix-codex`
- does not touch `src/jukebox/core/controller.py`, `src/jukebox/logging.py`, or `src/jukebox/main.py`, so the "scan event wasn't logged" part of the prompt remains unaddressed

## Implementation Comparison

### `dispatch()` strategy

| Line | Strategy | Consequence |
|---|---|---|
| `main` | transfer first, then play | assumes explicit transfer is required before a start |
| `playback-fix-codex` | direct play first, transfer fallback | tests whether transfer itself causes stale-context resurrection |
| `fix-glitch-kilo-opus` | direct play first, transfer fallback | keeps the same handoff hypothesis as `playback-fix-codex` |

### `status()` and `player_active()`

| Line | Behavior | Consequence |
|---|---|---|
| `main` | live Spotify calls | health, idle, and status observation consume API budget continuously |
| `playback-fix-codex` | still live Spotify calls | handoff logic improved, but background polling problem remained |
| `fix-glitch-kilo-opus` | passive cached values | restores zero background API calls for status and idle decisions |

### Startup probe behavior

| Line | Startup probe behavior | Consequence |
|---|---|---|
| `main` | auth-only probe, no device wait | avoids restart loops, but can enter runtime before the receiver is visible |
| `playback-fix-codex` | no preserved startup-probe change | boot behavior stays on the `main` contract |
| `fix-glitch-kilo-opus` at `03a26e6` | auth plus one device-resolution pass to seed passive cache | improves initial status accuracy, but still gives up immediately on `device_not_listed` |
| current worktree on `fix-glitch-kilo-opus` | auth plus bounded retry window for `device_not_listed` during `probe()` | directly targets post-boot receiver propagation delay without reintroducing idle polling |

### Playback confirmation heuristic

| Line | Heuristic | Consequence |
|---|---|---|
| `main` | requested item match, else any target-device playback can count as success | vulnerable to false positives when the target was already playing stale content |
| `playback-fix-codex` | requested item match, else target playback must differ from a prestart snapshot | stronger guard against stale metadata |
| `fix-glitch-kilo-opus` | requested item match, else any target-device playback can count as success | keeps `main`'s permissive fallback and therefore preserves the same code-level false-positive risk |

### Track payload policy

| Line | Track payload | Consequence |
|---|---|---|
| `main` | album context plus offset when album lookup succeeds, else single URI | preserves album context, but may carry more stale-session behavior |
| `playback-fix-codex` | replace-mode track cards use single URI via `stop_after_track`; queue fallback paths can still use context behavior | narrowed replace-mode starts but widened scope with stop-after-track logic |
| `fix-glitch-kilo-opus` | single URI for all track starts | simpler and more predictable, but it drops the stronger confirmation logic |

### Public interface changes

| Line | Interface change | Consequence |
|---|---|---|
| `main` | no `PlaybackRequest.stop_after_track` | simpler adapter contract |
| `playback-fix-codex` | adds `PlaybackRequest.stop_after_track` | makes controller intent explicit but introduces branch-only behavior not carried forward |
| `fix-glitch-kilo-opus` | no `PlaybackRequest.stop_after_track` | current branch does not retain the stop-after-track design |

### Rate-limit visibility

| Line | 429 handling | Consequence |
|---|---|---|
| `main` | no dedicated passive-status discipline | rate-limit pressure can be created by background polling |
| `playback-fix-codex` | no preserved rate-limit visibility improvement | handoff branch does not materially improve operator visibility into 429s |
| `fix-glitch-kilo-opus` at `03a26e6` | explicit `spotify_rate_limited` status and warning-level logging | makes 429 state visible and compatible with passive health |
| current worktree on `fix-glitch-kilo-opus` | explicit `Retry-After` rendering when Spotify provides it | improves operator guidance during throttling without changing control flow |

## What Went Wrong

### 1. Two problems got mixed together

The history shows two real issues:

- handoff correctness: did the receiver start the requested content, or did Spotify revive stale session state?
- API-discipline reliability: were background monitors consuming Spotify calls fast enough to trigger rate limiting?

`main` accumulated both problems in the same adapter.
`playback-fix-codex` mostly attacked the handoff problem.
`fix-glitch-kilo-opus` mostly attacked the API-discipline problem.

Result:

- both branches contain valid work
- neither branch is a complete answer to both problems

### 2. `main` accumulated conflicting assumptions

The final `main` line before the two fix branches effectively assumed all of the following at once:

- receiver visibility is only a dispatch-time concern
- health and idle paths may query Spotify live
- "target device is playing" is good enough as a fallback confirmation
- explicit transfer is required before play

Those assumptions point in different directions.
Some are about boot resilience, some about observability, and some about playback correctness.
Together they made the adapter harder to reason about and easier to "partially fix."

### 3. `fb8d3c6` created a real false-positive risk, but not a confirmed root cause

`fb8d3c6` made playback confirmation more tolerant of stale Spotify metadata.
That likely reduced false negatives, but it also made a more dangerous false positive possible:

- old content can keep playing on the target
- the target still counts as "playing"
- confirmation succeeds even though the requested content did not actually take over

`playback-fix-codex` is the only preserved line that directly tightened that hole again.

This is a real code-level risk.
It is not, by itself, proof that this was the dominant real-world cause of the observed device glitching.

### 4. The strongest handoff branch widened scope before it was merged

`playback-fix-codex` contains the best preserved evidence-driven handoff work:

- snapshot-based confirmation
- direct-play-first with transfer fallback
- a dedicated runbook and probe script

It also widened scope with:

- `stop_after_track`
- track-duration lookup
- background stop-monitor thread
- controller contract changes

That made the branch harder to adopt piecemeal.
The most valuable handoff safeguards were bundled with extra behavior that was not required to prove the original glitch fix.

### 5. The current branch fixed the strongest proven regression

`fix-glitch-kilo-opus` clearly fixes a real problem from `main`:

- it removes background Spotify polling from health and idle paths
- it caches tokens instead of refreshing every call
- it introduces explicit rate-limit status and operator-facing visibility

But it drops two important assets from `playback-fix-codex`:

- the snapshot-delta confirmation safeguard
- the probe-first reproduction tooling

Result:

- the branch is stronger on API discipline
- the branch is weaker on proving that stale-content false positives are gone

Given later real-device testing with current committed changes, the burden of proof is now on the snapshot-guardrail side:

- the branch already appears to have improved real behavior
- extra confirmation complexity now needs reproduction-based justification
- the snapshot safeguard should be treated as optional hardening until a current-branch replace-mode failure actually demonstrates the need

### 6. The diagnostic tooling was not carried forward

`playback-fix-codex` preserved a real investigation workflow in:

- `docs/spotify-connect-debug.md`
- `scripts/spotify_connect_probe.py`

Those are absent on the current branch.
That matters because later sessions then have to reason from code and symptoms again instead of starting from a preserved reproduction harness.

### 7. The latest prompt was a real boot incident, not the original stale-context reproduction

The 2026-04-16 prompt that drove the current worktree was about boot autonomy:

- the receiver stayed `device_not_listed`
- manual phone activation was needed
- scan observability also looked wrong

That is adjacent to the older handoff glitch, but it is not the same question.
It naturally pushed the Kilo or Opus session toward startup visibility and bounded readiness recovery instead of toward stale-context confirmation logic.

That direction was reasonable given the prompt.
It also means the session should be judged as a boot-recovery investigation first, not as a full replacement for the earlier handoff-focused branch.

### 8. Historic validation docs and live-device behavior diverged

The repo already contains strong reboot-success claims in `docs/pi-setup-log.md` for 2026-03-09.
The 2026-04-16 incident reported the opposite symptom on the real device.

That leaves three plausible explanations:

- a regression after the documented validation
- environment drift on the Pi or Spotify side
- stale validation docs that no longer describe the live appliance accurately

The current worktree implicitly treated the problem as a boot-time receiver-visibility delay and added bounded startup retries.
That is a sensible mitigation, but it does not by itself resolve the deeper documentation-versus-reality conflict.

## Competing Explanations And Confidence

This section replaces any overly certain single-root-cause reading.

### Highest-confidence conclusions

- `main` created a high-idle-call architecture that could trigger Spotify rate limiting. Confidence: `A`
- permissive confirmation could report success too early while Spotify state was still misleading or stale. Confidence: `A`
- `fix-glitch-kilo-opus` materially improves API discipline and 429 visibility. Confidence: `A`

### Leading current working theory

The best current explanation for the severe glitching behavior is:

- control-path degradation from hidden or under-surfaced rate limiting
- combined with permissive confirmation that made the system appear more successful than it really was

Confidence: `B`

This theory better matches the observed debugging detour:

- Spotify clients looked wrong
- the box appeared to do something
- logs did not make 429 pressure explicit enough
- later scans did not behave reliably

### Plausible but still unconfirmed contributor

There may also have been a separate UX issue around stale context or metadata propagation:

- Spotify clients showing old content
- progress bars or playing state reflecting earlier context
- scanned content actually being audible

That may have interacted with direct-play versus transfer behavior.
Confidence: `B-`

### Real code risk, but unconfirmed as the primary incident cause

Snapshot-based stale-content confirmation is still a valid safeguard against a real code-level false-positive path.
However:

- that path is not yet confirmed as the main reason for the real-world glitch
- the branch that implemented the safeguard also added unrelated runtime complexity
- recent anecdotal testing with current committed code suggests the problem may already be materially improved without that guardrail

Confidence that snapshot guardrails are required right now: `C`

### Open question to keep explicit

The unresolved question is not:

- "is snapshot confirmation a good idea in the abstract?"

It is:

- "does current committed replace-mode behavior still fail in a way that snapshot confirmation demonstrably prevents?"

Until that is proven, snapshot confirmation should remain a documented hardening candidate, not an assumed must-merge fix.

## Successful Session Workflow Notes

This section uses the later fix-session explanation as supplemental workflow evidence.
It matters because the successful one-shot did not merely land on a different theory.
It followed a stricter evidence path.

### 1. The session read the full control flow before proposing a fix

- `playback_spotify.py` was read as one sequential backend, not as isolated helpers
- `dispatch()` was treated as the key path: token refresh, device resolution, transfer, play, confirm
- controller entrypoints were checked so replace mode was not assumed to contain hidden context-clearing logic
- dead helpers were identified by checking real call sites instead of trusting method names

### 2. Running tests before edits prevented the wrong fix

- the existing tests already failed against the checked-in code before the successful patch
- that exposed drift around the older album-context path
- without that step, the session could have "fixed" the code toward stale tests instead of toward the real implementation and runtime behavior

### 3. The rate-limit finding was not accidental

- live validation surfaced real Spotify API throttling behavior
- the session followed the API responses instead of forcing every symptom into the stale-context story
- that exposed a second major issue family: token churn and background-call pressure
- the later `spotify_rate_limited` visibility and `Retry-After` work therefore came from evidence-following, not from random scope creep

### 4. The public Kilo debug description matches the workflow shape, but not the hidden details

- public Kilo docs describe `debug` as a systematic troubleshooting agent with full tool access
- that description matches the reported workflow shape: read broadly, narrow hypotheses, inspect live behavior, then fix
- but the repo still does not reveal the exact hidden debug-agent instructions, automatic context retrieval, or how much Opus 4.6 versus tooling differences changed the outcome

### 5. "Kilo fixed it in one shot" is still not proof that model choice alone caused the better diagnosis

- the better outcome may have come from model differences, tool defaults, context gathering, workflow discipline, or some combination
- that remains an explicit unknown and should not be collapsed into a single explanation

## Session And Tooling Observations

Everything in this section is an inference from the code history and the stated session setup, not a direct fact from the repo.

### Inference: the sessions optimized for different visible problems

`playback-fix-codex` looks like a branch that started from a reproduction mindset:

- capture prestart and poststart state
- distinguish stale metadata from real content change
- build a probe script

`fix-glitch-kilo-opus` looks like a branch that started from the currently visible code smells and runtime architecture:

- live polling in health and idle paths
- token refresh churn
- missing rate-limit status
- passive-cache design rules

That difference alone is enough to send two frontier models in different directions even with the same opening prompt.

### Inference: missing carry-forward context mattered more than raw model quality

The current branch appears to have started with `AGENTS.md` and `README.md` only, plus the live workspace.
That gives strong guidance about:

- specs
- runtime behavior
- API discipline
- repository workflow

It does not automatically expose:

- the prior probe workflow
- the reproduction script
- the exact stale-context evidence gathered in the earlier branch

That likely biased the session toward fixing the locally visible rate-limit architecture rather than reconstructing the older handoff investigation.

### Inference: tool choice changed what was easiest to preserve

The Codex VS Code plugin sessions appear to have preserved more branch-local investigation artifacts:

- a dedicated runbook
- a dedicated probe script
- narrower commit checkpoints around hypotheses

The Kilo debug-mode session appears to have concentrated work in one larger backend-and-tests change plus local dirty edits.
That is not inherently worse, but it makes it easier for the process fix to replace the investigation tooling rather than incorporate it.

### Inference: the latest prompt strongly biased the session toward startup recovery

Unlike the older handoff-focused work, the 2026-04-16 prompt began with:

- a boot failure on the real box
- `receiver_unavailable`
- manual phone activation requirement
- apparent missing scan logging

Given that opening, it is unsurprising that the current worktree concentrated on:

- boot-time device visibility retries
- startup probe configuration
- clearer 429 operator messages

It is also unsurprising that it did not reconstruct the snapshot-confirmation logic from `playback-fix-codex` unless that prior branch was explicitly pulled into context.

## Conclusions To Lock

- `playback-fix-codex` kept the stronger stale-metadata safeguard and added the only preserved reproduction tooling.
- `playback-fix-codex` also widened scope with stop-after-track behavior and a background worker, which made selective adoption harder.
- `fix-glitch-kilo-opus` fixes a real `main` regression by removing background Spotify polling and token churn.
- `fix-glitch-kilo-opus` keeps the direct-play-first improvement but drops the snapshot safeguard and the probe tooling.
- the current worktree adds a bounded startup retry window that directly targets the 2026-04-16 boot-autonomy incident.
- the current worktree still does not address the "scan event wasn't logged" symptom from that prompt.
- the strongest evidence-backed problem is misleading success combined with weak 429 visibility, not a confirmed stale-content root cause.
- rate limiting is now a first-class competing explanation for the observed glitching behavior, not a side note.
- the rate-limit discovery should be treated as evidence-led API diagnosis, not as an accidental side quest.
- snapshot-based confirmation remains a valid hardening idea, but it is not yet justified as required runtime complexity.
- the exact contribution of Kilo debug-mode behavior and Opus 4.6 remains unknown.
- The current branch therefore improves API-discipline reliability and may already address much of the real issue, but it does not yet prove that all replace-mode edge cases are clean.

## Future Session Playbook

### Fixed reproduction matrix

Every future session should begin with the same matrix:

- transfer first vs direct play first
- context payload vs single-URI payload
- target idle vs target already playing stale content
- target visible vs target not visible
- cold boot with receiver not yet visible vs cold boot with receiver already visible
- idle runtime with no scans

The session should not change backend code before at least one row in that matrix is exercised or simulated.

### Probe-first workflow

If `scripts/spotify_connect_probe.py` is not merged into the active branch, recreate an equivalent probe before changing backend logic.
The minimum preserved outputs should be:

- exact command used
- play payload used
- preflight state
- post-transfer state
- post-play state
- matching `spotifyd` log excerpt when available

### API budget as an acceptance criterion

Treat these as non-negotiable:

- zero Spotify API calls from health monitoring
- zero Spotify API calls from idle monitoring
- zero Spotify API calls from status endpoints
- bounded API calls per scan
- explicit `spotify_rate_limited` status

### Evidence and confidence grading are now mandatory

Every future retro or post-mortem on this subsystem should include:

- claim
- evidence source
- confidence grade
- contradiction or uncertainty
- next assumption test

Do not allow branch intent to silently become root-cause certainty.

### Assumption testing before complexity

Before merging a harder fix, state the exact assumption it depends on and how to test it.

Examples:

- assumption: current replace mode still has a stale-content false-positive bug
- test: reproduce replace-mode failure on current committed code and show snapshot confirmation prevents it

- assumption: rate limiting is a major contributor
- test: capture logs during a glitch and confirm `spotify_rate_limited` or clear API-pressure symptoms

### Split future work into two hypothesis branches

Do not mix these into one branch again:

- playback-handoff correctness branch
- passive-status and rate-limit-discipline branch

That keeps confirmation logic and API-budget logic independently reviewable.

### Preserve carry-forward notes after every session

Every session should leave a short carry-forward note with:

- hypotheses tested
- evidence captured
- changes to keep
- changes to drop
- remaining real-Pi unknowns

Without that note, the next session is likely to reframe the problem from the current codebase instead of continuing the prior investigation.

### Reconcile incident evidence with existing docs before coding

When a live-device prompt contradicts an existing validation claim:

1. treat the validation docs as potentially stale
2. capture the exact incident evidence first
3. decide whether the issue is regression, environment drift, or documentation drift
4. only then start changing code

The 2026-04-16 boot incident should have been explicitly compared against the 2026-03-09 reboot claims in `docs/pi-setup-log.md` at the start of the session.

### Always pull forward prior branch tooling when the bug family matches

If a prompt touches Spotify handoff, receiver visibility, or stale playback metadata, the session context pack should include:

- this retro
- `playback-fix-codex` diffs for `src/jukebox/adapters/playback_spotify.py`
- the old probe script and runbook when available
- the current `docs/api-discipline.md`

Do not start from `README.md` and `AGENTS.md` alone for this subsystem again.

## Recommended Next Integration Shape

The immediate merge target should stay conservative.

Carry forward now:

1. keep the passive-status and token-caching work from `fix-glitch-kilo-opus`
2. keep the current worktree's bounded startup retry window for `device_not_listed`
3. keep the current worktree's `Retry-After` visibility improvement for 429s
4. restore the probe script and runbook from `playback-fix-codex`

Defer unless validation proves the need:

5. snapshot-delta confirmation safeguard

Do not carry forward without separate product justification:

6. `PlaybackRequest.stop_after_track`
7. background stop-monitor thread
8. controller behavior changes tied only to stop-after-track

That produces a narrower merged target with lower complexity:

- direct-play-first handoff behavior
- bounded boot-time receiver visibility recovery
- zero background Spotify polling
- clearer rate-limit operator feedback
- preserved reproduction tooling

## Post-Review Forward Plan

This is the recommended merge plan after user review of the retro findings.

### Phase 1: Land the low-risk runtime and observability fixes

Carry forward from `fix-glitch-kilo-opus` and the current worktree:

- passive cached `status()`
- passive cached `player_active()`
- token caching
- explicit `spotify_rate_limited` status and warning logging
- `Retry-After` message rendering for 429s
- bounded startup `device_not_listed` retries in `probe()`

Acceptance criteria:

- zero Spotify API calls from health, idle, and status paths
- bounded startup probe cost
- boot reaches `ready` autonomously when receiver visibility appears within the configured retry window
- boot degrades cleanly to `receiver_unavailable` when the retry window expires

### Phase 2: Validate replace mode before adding more runtime complexity

Before merging snapshot confirmation, run targeted validation on current committed code plus low-risk observability fixes:

- let at least one replace-mode track run through or run enough sequential replace scans to expose the old symptom
- test paused old album context on another client, then scan on jukebox
- test replace mode separately from queue mode
- watch specifically for `spotify_rate_limited`, `receiver_unavailable`, and playback success lines
- confirm whether manual playback pull on phone or desktop is ever still required

Acceptance criteria:

- if replace mode behaves correctly, do not merge snapshot guardrails
- if replace mode still shows client-state divergence or success without reliable takeover, revisit snapshot confirmation as targeted hardening
- if snapshot confirmation is revived, it must be justified by a current-branch reproduction, not only by historical suspicion

### Phase 3: Restore diagnostic tooling and only then reconsider deferred hardening

Carry forward from `playback-fix-codex`:

- probe script
- runbook

Only after Phase 2 and Phase 3 should the team decide whether to revive:

- prestart playback snapshots
- snapshot-delta confirmation safeguard

### Phase 4: Revalidate the real Pi and close the prompt gap

Run on `jukebox.local`:

- cold boot with no manual phone activation
- repeated reboot
- one scan while receiver is still recovering
- one scan after `ready`
- replace-mode reproduction matrix
- idle runtime API-budget check

Also explicitly verify the unresolved part of the 2026-04-16 prompt:

- whether `scan_received` and the later scan outcome events are actually missing from logs
- whether the issue is event emission, logger routing, journal truncation, or operator interpretation

### Phase 5: Persist spec and documentation updates in the same review batch

If bounded startup retries are merged, update:

- `README.md`
- `docs/api-discipline.md`
- `docs/pi-setup.md`
- `docs/pi-validation.md`
- `docs/pi-setup-log.md` after real Pi revalidation
- `spec/EPIC-3-technical.md` because the startup readiness contract changes

If snapshot-based confirmation and probe tooling are merged, update:

- `docs/spotify-connect-debug.md`
- `spec/EPIC-4-technical.md` because playback confirmation behavior changes
- this retro, replacing branch-only notes with merged-state notes

Do not let code land first and leave the specs behind.

## Workflow Changes To Adopt Now

- Start each agent session on this subsystem with a carry-forward pack: current incident prompt, this retro, relevant branch diffs, and the current Pi validation notes.
- Separate the prompt into symptom, hypothesis, and acceptance criteria before editing code.
- Require an evidence/confidence table in every retro or post-mortem touching multi-session debugging.
- Require an explicit assumption-testing plan before adding runtime complexity to address an unconfirmed theory.
- Keep branch scope hypothesis-focused. Do not bundle handoff correctness, playback features, and runtime recovery in one change unless each part is independently justified.
- Preserve diagnostic tooling early. A probe script or runbook is not optional once a bug requires multi-step external-state reasoning.
- When a real-device incident contradicts existing docs, treat doc revalidation as part of the task, not as optional cleanup.
- Require spec and doc patches in the same review batch as any accepted runtime behavior change.

## Known Unknowns

- abandoned or omitted branch-local experiments that never reached a commit
- whether the stale-context glitch was fully reproduced on every environment or only on selected Pi and Spotify-session states
- whether the current branch's direct-play-first approach is sufficient on its own in all real `spotifyd` cases without any additional confirmation guardrails
- whether the 2026-04-16 boot incident was a code regression, environment drift, or a stale-doc mismatch
- whether replace mode on current committed code still has any real stale-content takeover failure
- why the scan event appeared to be missing from logs during the 2026-04-16 incident
- the exact contribution of Kilo Code's built-in debug agent behavior, automatic context gathering, and Opus 4.6 relative to the earlier Codex GPT-5.4 sessions
