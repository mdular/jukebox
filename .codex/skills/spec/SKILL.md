---
name: spec
description: Create and update per-EPIC requirements and technical design documents for the QR Card Jukebox repo. Use when asked to draft `spec/EPIC-<n>-requirements.md` from `spec/roadmap.md` and `spec/concept.md`, to structure EPIC decisions as `[ ]` or `[x]` checklists, or to turn decided requirements into `spec/EPIC-<n>-technical.md` aligned to the current codebase.
---

# Jukebox EPIC Specs

Use this skill to produce the per-EPIC specification docs under `spec/` for the jukebox repo.
Keep the requirements document decision-heavy and the technical design implementation-shaped.

## Read First

Read these files before writing either document:

- `spec/concept.md`
- `spec/roadmap.md`
- `spec/README.md`

Read these files when they exist for the target EPIC:

- `spec/EPIC-<n>-requirements.md`
- `spec/EPIC-<n>-technical.md`
- legacy `spec/EPIC-<n>.md`

Before writing a technical design, inspect the current repo state so the design matches the actual package layout, scripts, tests, and runtime scaffolding.

## Workflow

1. Identify the target EPIC number from the user request and confirm the canonical filenames:
   - `spec/EPIC-<n>-requirements.md`
   - `spec/EPIC-<n>-technical.md`
2. Draft or update the requirements doc first unless the user explicitly asks only for technical design and the decisions are already taken.
3. Keep open choices in the requirements doc as flat checklist options.
4. Wait for decisions to be taken, usually shown with `[x]`, before creating or revising the technical design.
5. When drafting the technical design, translate the selected decisions into concrete modules, interfaces, runtime flow, configuration, and tests that fit the current repo.

## Requirements Document Rules

Read [references/requirements-outline.md](references/requirements-outline.md) when drafting or revising `spec/EPIC-<n>-requirements.md`.

Apply these rules:

- Use headings and short context above each decision list.
- Format options as flat checklist items: `- [ ] ...` or `- [x] ...`.
- Mark the recommended option with `(Recommended)`.
- Preserve existing user decisions and checked boxes.
- Keep implementation details out of the requirements doc unless they are necessary to define externally visible behavior.
- Add `Related decision` references from requirement sections back to the relevant decision IDs when useful.
- Write acceptance criteria as clear Given/When/Then style bullets.

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

## Writing Constraints

- Treat `spec/concept.md` as the product source of truth and `spec/roadmap.md` as the sequencing source of truth.
- Do not invent requirements, hardware behavior, or workflows outside the existing specs.
- When a legacy EPIC doc exists under a different name, read it and migrate its useful content into the canonical filename instead of creating conflicting duplicates.
- Keep the requirements doc easy to review by humans.
- Keep the technical design specific enough that implementation can start from it.
