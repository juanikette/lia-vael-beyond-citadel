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

## Build, Test, and Lint (Current State)

No build, test, or lint tooling is currently defined in this repository.

- No tool manifests are present (for example `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, or `.csproj`).
- No single-test command is available yet.

When tooling is added, document full build/test/lint commands and a single-test command.

## Guiding Question

> "Does this feel like something BioWare could have shipped?"
