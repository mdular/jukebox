---
name: requirements
description: Draft and update per-EPIC requirements documents for the QR Card Jukebox repo. Use when asked to create or revise `spec/EPIC-<n>-requirements.md` from `spec/roadmap.md` and `spec/concept.md`, preserve checked decisions, and structure open choices as flat checklist items.
---

# Jukebox EPIC Requirements

Use this skill to produce the per-EPIC requirements docs under `spec/` for the jukebox repo.
Keep the session focused on requirements decisions and acceptance criteria only.

## Read First

Read these files before writing the requirements document:

- `spec/concept.md`
- `spec/roadmap.md`
- `spec/README.md`

Read these files when they exist for the target EPIC:

- `spec/EPIC-<n>-requirements.md`
- legacy `spec/EPIC-<n>.md`

If `spec/EPIC-<n>-technical.md` already exists, read it only to identify decision drift that should be called out. Do not revise the technical design in this session.

## Workflow

1. Identify the target EPIC number from the user request and confirm the canonical filename:
   - `spec/EPIC-<n>-requirements.md`
2. Draft or update the requirements doc.
3. Keep open choices as flat checklist options.
4. Preserve existing user decisions and checked boxes.
5. If the user asks for technical design work, stop at the requirements outcome and direct the next session to `$spec` after decisions are taken.

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

## Session Boundary

- This skill owns requirements only.
- Do not draft or revise `spec/EPIC-<n>-technical.md` in the same session.
- If technical design work is needed, use `$spec` in a separate session after the relevant requirements decisions are marked.

## Writing Constraints

- Treat `spec/concept.md` as the product source of truth and `spec/roadmap.md` as the sequencing source of truth.
- Do not invent requirements, hardware behavior, or workflows outside the existing specs.
- When a legacy EPIC doc exists under a different name, read it and migrate its useful content into the canonical filename instead of creating conflicting duplicates.
- Keep the requirements doc easy to review by humans.
