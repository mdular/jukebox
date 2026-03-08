# Requirements Outline

Use this outline for `spec/EPIC-<n>-requirements.md`.
Adjust section names only when the EPIC clearly needs it.

## Recommended Sections

- `# EPIC <n> Requirements Specification`
- `## Title`
- `## Purpose`
- `## Objective`
- `## Success Definition`
- `## Decision Checklist`
- `## In Scope`
- `## Out of Scope`
- `## Functional Requirements`
- `## Non-Functional Requirements`
- `## Acceptance Criteria`
- `## Deliverables`
- `## EPIC <n+1> Handoff Questions` or `## Handoff Questions`
- `## Notes`

## Decision Checklist Pattern

For each decision:

1. Add a heading such as `### D-1 Scan Input Coverage`.
2. Add one short context paragraph explaining why the decision matters.
3. Add a flat checklist of options.
4. Mark the preferred choice with `(Recommended)`.
5. Leave options unchecked unless the user has already taken the decision.

Example pattern:

```md
### D-1 Example Decision

One short paragraph explaining the decision and the tradeoff.

- [ ] Option A
- [ ] Option B (Recommended)
- [x] Option C
```

## Requirements Section Pattern

- Keep requirement statements behavioral, not implementation-specific.
- Use IDs such as `FR-1`, `FR-2`, `NFR-1`, `AC-1`.
- Add `Related decision:` references where they help connect the checklist to the requirement.
- Keep acceptance criteria observable and testable.

## Guardrails

- Keep the document easy to scan.
- Do not collapse multiple decision sets into a single dense line.
- Do not turn the requirements doc into a technical design.
- Do not drop recommended options just because the user has not decided yet.
