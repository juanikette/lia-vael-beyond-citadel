# Lia'Vael: Beyond Citadel — Narrative Expansion Mod (Mass Effect 2)

## Instruction Entry Point

Use this file as the **operational entry point** for AI agents.

- Detailed project guidance lives in `docs/`.
- Human-facing project summary lives in `README.md`.
- Toolkit design lives in `tools/pcc-toolkit/DESIGN.md`.

## Session Lifecycle

Every agent session follows this protocol:

### Open

1. Read `.opencode/current.md` — understand where the last session left off.
2. Pick **one** task. If multiple are pending, take the highest-priority one.
3. Update `.opencode/current.md`: set phase, task, branch, plan.
4. If using Notion, move the phase page to `In Progress`.

### Work

- Document in `.opencode/current.md` as you go, not at the end.
- Work incrementally, following the defined phase order.
- Prefer additive, low-intrusion changes over replacements.
- Validate dialogue triggers and mission-state conditions carefully.
- Avoid touching unrelated systems.

### Close

1. Verify deliverables against `.opencode/checkpoints.md`.
2. If complete: mark phase/task as `Done` in Notion.
3. Move `.opencode/current.md` summary to `.opencode/history.md` (append-only).
4. Clear `.opencode/current.md` back to the template.
5. Push branch to remote.
6. No temporary files, no debug prints, no orphaned TODOs.

## Read First

`docs/` contains the project's design principles, constraints, phase order, character role rules, narrative guidelines, and technical focus areas. Read them before making narrative or gameplay changes. `README.md` provides the project overview.

## Repository Map

| Path | What it contains | When to read |
|------|-----------------|--------------|
| `.opencode/current.md` | Active session state | Every session start |
| `.opencode/history.md` | Append-only session log | For historical context |
| `.opencode/checkpoints.md` | Objective completion criteria | Before closing any phase |
| `.opencode/conventions.md` | Code style rules for all languages | Before writing code |
| `.opencode/verification.md` | How to prove work is correct | Before marking a task done |
| `docs/` | Design principles, constraints, narrative rules | Before making narrative changes |
| `tools/pcc-toolkit/DESIGN.md` | v2 toolkit architecture | Before toolkit work |

## Operational Rules (High Impact)

- Work incrementally, following the defined phase order.
- Prefer additive, low-intrusion changes over replacements.
- Keep modifications isolated and reversible where possible.
- Validate dialogue triggers and mission-state conditions carefully.
- Avoid touching unrelated systems.
- **Always consult the LegendaryExplorer repository** when implementing toolkit features. Use GitHub search (`github_search_code` / `github_get_file_contents`) against `github.com/ME3Tweaks/LegendaryExplorer` to understand how the official tool handles PCC parsing, TLK resolution, dialogue editing, and graph rendering. LEX is the reference implementation — match its behavior unless DESIGN.md specifies otherwise.

## Language Policy

- Use English for all repository-facing content.
- Documentation, code comments, variable names, function/class identifiers, user-facing strings, error messages, and test descriptions should be written in English.
- **Exception**: Notion Kanban pages and reports may be written in Spanish.

## Notion Tracking Workflow

The Kanban board `PCC Dialog Toolkit - Kanban` is the execution log for toolkit development.

- **When starting a new phase**: create a new page in the Kanban. Set `Phase` to the phase name, `Status` to `TO-DO`.
- **When beginning work**: move `Status` to `In Progress`. Update `.opencode/current.md`.
- **During the phase**: keep the Notion page updated with scope, deliverables, risks, and verification notes as work advances.
- **When complete**: move `Status` to `Done`. Verify against `.opencode/checkpoints.md` first.
- If extra tasks appear outside the original phase plan, add them as new Kanban items.
- Keep Notion updates aligned with repository state (do not mark `Done` without corresponding code/docs progress).

## Build, Test, and Lint

Tooling exists in the toolkit subprojects:

- **Go core** (`tools/pcc-toolkit/core/`): `go test ./...`, `go build ./cmd/pcc-core/`
- **Python CLI** (`tools/pcc-toolkit/cli/`): `pytest` (once implemented)

No top-level build command exists yet. When one is added, document it here.

## Guiding Question

> "Does this feel like something BioWare could have shipped?"
