# Technical Outline

Use this outline for `spec/EPIC-<n>-technical.md` after the requirements decisions are taken.

## Preconditions

- Read `spec/EPIC-<n>-requirements.md` and identify the checked decisions.
- Review the current repo state before writing the design.
- If checked decisions conflict with acceptance criteria or each other, call that out explicitly and resolve it in the document.

## Recommended Sections

- `# EPIC <n> Technical Design`
- `## Purpose`
- `## Selected Decisions Carried Into This Design`
- `## Design Goals`
- `## Non-Goals`
- `## Current Baseline`
- `## Architecture`
- `## Runtime Flow`
- `## Module Plan`
- `## Data Model`
- `## Configuration Design`
- `## Feedback and Logging Design`
- `## Testing Strategy`
- `## Failure Handling`
- `## Implementation Sequence`
- `## Risks` or `## Open Risks`

## Technical Design Pattern

- Translate each checked decision into a concrete design choice.
- Anchor design sections to real files, packages, and scripts that already exist.
- Keep the controller logic, domain logic, and side-effect adapters separate.
- Make the design implementation-ready without hard-coding speculative future work.

## Guardrails

- Do not write the technical design as a restatement of the requirements.
- Do not invent runtime dependencies unless the repo or the selected decisions justify them.
- Do not ignore existing scaffolding such as `README.md`, `pyproject.toml`, `src/`, `tests/`, `scripts/`, or deployment files when they affect the design.
- Prefer a small number of clear modules over a vague architecture section.
