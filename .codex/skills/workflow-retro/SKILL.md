---
name: workflow-retro
description: Reassess stalled debugging, repeated failed fixes, or conflicting explanations. Use when the current diagnosis, solution path, or agent workflow may itself be wrong, and before continuing another iteration.
---

# Workflow Retro

Use this skill when debugging is not converging, multiple fix branches have failed, logs and behavior do not line up with the current explanation, or either the user or the AI is presenting low-confidence assumptions as confident conclusions.

When this skill is invoked, assume something is not working in the current approach. Do not continue iterating on fixes by default. First question the diagnosis, the proposed solution, and the workflow that produced them.

Treat the output as a hybrid retro and post-mortem:

- `retro`: what the team and agent workflow did, what assumptions were made, and how the process drifted
- `post-mortem`: what failed, what evidence exists, what remains unproven, and what to change next

## Trigger Conditions

Use this skill when one or more of these conditions hold:

- Multiple sessions, branches, or agents have worked on the same issue without a stable fix.
- The current explanation depends more on inference than on logs, tests, code history, or reproduction.
- A branch added significant complexity without a confirmed problem it solves.
- Runtime behavior, client UX, or logs appear contradictory.
- A bugfix attempt seems to have created a new theory rather than resolving the old one.
- Tooling, prompting, environment setup, or workflow differences may have changed the direction of the work.
- The user asks for a retro, post-mortem, reconstruction, confidence check, or branch comparison.

## Operating Stance

Apply these rules throughout the workflow:

- Treat user assumptions and AI assumptions with the same skepticism.
- Separate what is proven from what is inferred.
- Prefer reversible, low-risk observability improvements over speculative runtime complexity.
- Do not infer root cause from branch intent alone.
- Do not treat "we wrote a fix for X" as evidence that X was the real problem.
- Label omitted, abandoned, or unpublished experiments as `unknown`.
- If current committed behavior already looks acceptable in real use, raise the bar for adding more code complexity.

## Workflow

### 1. Freeze The Current Iteration

Stop the blind fix loop before proposing more changes.

Capture:

- the current issue statement
- the leading explanation or explanations
- the branch or worktree changes under discussion
- the missing evidence that prevents a confident conclusion

### 2. Rebuild The Evidence Record

Collect the raw material before interpreting it:

- dated symptoms and incident notes
- exact logs and error messages
- relevant commits, branches, and diffs
- tests, reproductions, and non-reproductions
- environment details that matter
- prompt, tool, or workflow differences if they plausibly affected the result

For each item, note whether it is:

- direct evidence
- anecdotal evidence
- inference from code history
- unknown or missing

### 3. Decompose Every Major Claim

For each important statement, classify it as one of:

- `Observation`
- `Interpretation`
- `Assumption`
- `Conclusion`

Rewrite any conclusion that is really an assumption.

Examples of statements that require downgrading:

- "This branch fixed the root cause"
- "The glitch was caused by stale content"
- "The direct-play change introduced the regression"

If the evidence does not prove the statement, say so explicitly.

### 4. Grade Confidence

Assign each major claim a confidence grade:

- `A`: directly supported by code history, logs, tests, or confirmed reproduction
- `B`: strong inference with multiple supporting signals, but still not directly proven
- `C`: plausible theory or partial fit
- `D`: speculation, intuition, or weak workflow guess

Rules:

- Do not present `B`, `C`, or `D` claims as settled facts.
- Say what evidence would upgrade or downgrade the claim.
- If confidence changes during the analysis, revise it explicitly.

### 5. Build Competing Hypotheses

Do not stop at the first plausible explanation.

For each hypothesis, state:

- what it explains
- what it does not explain
- what evidence supports it
- what evidence weakens it
- what would falsify it
- whether it requires code changes, observability changes, workflow changes, or no changes yet

If root cause is not proven, maintain at least two live hypotheses.

### 6. Audit The Workflow, Not Just The Code

Assume the workflow may have contributed to the bad outcome.

Question:

- Was the prompt framing too narrow too early?
- Did tool or environment differences push the work in a different direction?
- Was repository context insufficient at session start?
- Did the team mix multiple hypotheses into one branch?
- Did missing logs or poor surfacing send the work down a detour?
- Did branch intent get mistaken for proof of root cause?
- Did the work add complexity before validating current committed behavior?
- Did either the user or the AI state a low-confidence theory too confidently?

Record concrete workflow corrections, not just observations.

### 7. Decide What To Carry Forward

Split changes into three groups:

- `Merge now`: low-risk, evidence-backed improvements worth keeping
- `Defer`: plausible hardening or design ideas without confirmed need
- `Drop`: disproven, scope-crept, or unjustified changes

For each item, include:

- why it belongs in that bucket
- the evidence and confidence grade
- the remaining unknowns
- the docs or specs that must be updated if it lands

### 8. Define An Assumption-Testing Plan

Before adding more code, create a validation matrix that tests the leading theories.

Include:

- exact modes or scenarios to exercise
- expected behavior
- logs, metrics, or state transitions to watch
- at least one test aimed at falsifying the leading explanation

If a proposed hardening change cannot be tied to a concrete failing scenario, keep it deferred.

### 9. Persist The Learning

Capture the results in a durable artifact such as a retro, post-mortem, or design note.

Persist:

- timeline with dates and commit hashes
- evidence ledger
- confidence table
- competing hypotheses
- workflow failures and corrections
- merge, defer, and drop decisions
- validation plan
- required spec and doc follow-ups

If runtime behavior, workflow rules, or debugging expectations change, update the corresponding docs or specs alongside the code changes that adopt them.

## Output Structure

Prefer this shape unless the user requests something else:

1. `Problem Statement`
2. `What Is Proven`
3. `What Is Inferred`
4. `Competing Hypotheses`
5. `Confidence Table`
6. `Workflow Failures`
7. `Merge / Defer / Drop`
8. `Validation Matrix`
9. `Required Spec And Doc Updates`
10. `Carry-Forward Note`

## Guardrails

- Do not continue the current implementation loop until the diagnosis and workflow have been challenged.
- Do not let either the user or the AI turn a `C` or `D` claim into a conclusion.
- Do not merge complexity because it feels safer; require evidence or a clear low-risk observability benefit.
- Do not confuse improved guardrails with a proven root-cause fix.
- Do not erase conflicting evidence; make the contradiction explicit.
- Do not let missing data stay implicit. Call it out as a blocker or unknown.

## Session Pattern To Reuse

- compare code history before drawing conclusions
- separate branch behavior from branch intent
- re-grade confidence when new runtime evidence appears
- treat anecdotal device validation as meaningful but not conclusive
- prefer validating current committed behavior before merging speculative hardening
- treat evidence grading and assumption testing as part of the retro itself

Use that pattern whenever a debugging effort has become expensive, repetitive, or theory-heavy.
