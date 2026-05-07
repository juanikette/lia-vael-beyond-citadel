# Lia'Vael: Beyond Citadel — Narrative Expansion Mod (Mass Effect 2)

## 🤖 Instruction Entry Point

Use this file as the **operational entry point** for AI agents.

- Detailed project guidance lives in `docs/`.
- Human-facing project summary lives in `README.md`.

## Read First

1. `docs/README.md`
2. `README.md` (project overview, scope boundaries, and narrative intent)
3. `docs/design-principles.md`
4. `docs/phase-order.md`
5. `docs/constraints.md`
6. `docs/character-role-rules.md`
7. `docs/technical-focus-areas.md`
8. `docs/narrative-guidelines.md` (additional tone examples)

## Operational Rules (High Impact)

- Work incrementally, following the defined phase order.
- Prefer additive, low-intrusion changes over replacements.
- Keep modifications isolated and reversible where possible.
- Validate dialogue triggers and mission-state conditions carefully.
- Avoid touching unrelated systems.

## Notion Tracking Workflow

When a Kanban or task board exists in Notion for the active workstream (for example, `PCC Dialog Toolkit - Kanban`), treat it as a required execution log.

- Keep each phase page updated with scope, deliverables, risks, and verification notes.
- Move status values (`TO-DO` -> `In Progress` -> `Done`) as work advances.
- If extra implementation tasks appear outside the original phase plan, add them as new Kanban items.
- Record meaningful progress before and after major implementation steps.
- Keep Notion updates aligned with repository state (do not mark `Done` without corresponding code/docs progress).

## Build, Test, and Lint (Current State)

No build, test, or lint tooling is currently defined in this repository.

- No tool manifests are present (for example `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, or `.csproj`).
- No single-test command is available yet.

When tooling is added, document full build/test/lint commands and a single-test command.

## Guiding Question

> "Does this feel like something BioWare could have shipped?"
