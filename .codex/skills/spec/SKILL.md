---
name: spec
description: Create and update per-EPIC technical design documents for the QR Card Jukebox repo. Use when asked to draft or revise `spec/EPIC-<n>-technical.md` from the checked decisions in `spec/EPIC-<n>-requirements.md` and align the design to the current codebase.
---

# Jukebox EPIC Technical Specs

Use this skill to produce the per-EPIC technical design docs under `spec/` for the jukebox repo.
Keep the session focused on implementation-shaped technical design only.

## Read First

Read these files before writing the technical design:

- `spec/concept.md`
- `spec/roadmap.md`
- `spec/README.md`

Read these files for the target EPIC:

- `spec/EPIC-<n>-technical.md`
- `spec/EPIC-<n>-requirements.md`
- legacy `spec/EPIC-<n>.md`

Before writing a technical design, inspect the current repo state so the design matches the actual package layout, scripts, tests, and runtime scaffolding.

## Workflow

1. Identify the target EPIC number from the user request and confirm the canonical filenames:
   - `spec/EPIC-<n>-technical.md`
2. Read `spec/EPIC-<n>-requirements.md` and identify the checked decisions that govern the design.
3. If the requirements decisions are not taken, stop and direct the next session to `$requirements` unless the user explicitly asks you to proceed with stated assumptions.
4. Draft or update `spec/EPIC-<n>-technical.md`.
5. Translate the selected decisions into concrete modules, interfaces, runtime flow, configuration, and tests that fit the current repo.

## Technical Design Rules

Read [references/technical-outline.md](references/technical-outline.md) when drafting or revising `spec/EPIC-<n>-technical.md`.

Apply these rules:

- Do not write the technical design until the requirements decisions are taken or the user explicitly asks to proceed with assumed decisions.
- Review the repo state first: package layout, entrypoints, config, scripts, tests, docs, and deployment scaffolding as needed.
- Translate checked decisions into concrete architecture and implementation choices.
- Tie the design to actual file paths and modules in the repo.
- Call out any tension between checked decisions, requirements, and acceptance criteria, then resolve or document the assumption explicitly.
- Keep a clean separation between core logic and side-effect adapters.
- Avoid inventing dependencies, infrastructure, or deployment behavior not justified by the repo or the selected decisions.

## Session Boundary

- This skill owns technical design only.
- Do not draft or revise `spec/EPIC-<n>-requirements.md` in the same session.
- If requirements decisions are missing or need revision, use `$requirements` in a separate session first.

## Writing Constraints

- Treat `spec/concept.md` as the product source of truth and `spec/roadmap.md` as the sequencing source of truth.
- Do not invent requirements, hardware behavior, or workflows outside the existing specs.
- When a legacy EPIC doc exists under a different name, read it and migrate its useful content into the canonical filename instead of creating conflicting duplicates.
- Keep the technical design specific enough that implementation can start from it.
