# Agent Guidelines

- Follow the specs in [`spec/`](/Users/markus/Workspace/jukebox/spec) for all implementation work.
- Treat [`spec/concept.md`](/Users/markus/Workspace/jukebox/spec/concept.md) as the source of truth for product direction.
- Do not invent requirements, workflows, hardware identifiers, credentials, or behavior not present in the specs.
- Prefer small, incremental, reviewable changes over large refactors.
- Keep Raspberry Pi 3 and headless Linux runtime constraints in mind.
- Avoid heavy dependencies unless a current spec justifies them.
- Separate hardware adapters from core logic so the core remains testable.
- Keep code runnable and testable on non-Pi development machines whenever possible.
- Use environment variables for secrets and never commit credentials.
- Update technical docs when changing repository structure or developer workflow.
- Keep stubs honest: no fake QR payloads, fake Spotify credentials, or placeholder business content.
