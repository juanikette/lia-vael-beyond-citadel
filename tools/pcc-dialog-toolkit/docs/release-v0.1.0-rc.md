# pcc-dialog-toolkit v0.1.0-rc (scope OT)

Date: 2026-05-08

Release status: approved candidate for ME2 OT.

## Summary

- A stable MVP pipeline for `BioConversation` extraction is consolidated with versioned JSON output (`schema_version=0.1`).
- Base TLK + DLC override resolution flow is validated on real OT samples.
- Phase 6 QA is documented with partial closure: OT validated, LE2 pending environment availability.

## Included scope

- PCC package reading and `BioConversation` export detection.
- Conversation structure parsing into a normalized AST.
- `StrRef` resolution via base TLK and DLC TLKs with `MountPriority` precedence.
- Final JSON serializer with validated contract:
  - valid `conversations`
  - per-conversation `errors` (without aborting the file)
  - aggregated `summary` (`ok/failed/warnings`)

## Validation evidence

- Expanded OT QA:
  - `files=25`
  - `files_with_conversations=11`
  - `conversations_total=11`
  - `conversations_ok=11`
  - `conversations_failed=0`
  - `warnings_total=0`
  - `nonzero_returncodes=0`
- Manual OT LEX cross-check:
  - `cases=3`
  - `OK=3`
  - `Mismatch=0`
  - `N/A=0`

## Known limitations

- LE2 coverage was not executed in this cycle due to lack of local Legendary Edition installation.
- Full OT/LE closure remains pending re-running the runbook in an LE2 environment.

## Artifacts

- Expanded OT report:
  - `tools/pcc-dialog-toolkit/output/phase6-ot-expanded/phase6-ot-expanded-report.json`
- Control lines for LEX cross-check:
  - `tools/pcc-dialog-toolkit/output/phase6-ot-expanded/phase6-ot-lex-control-lines.json`
- QA runbook:
  - `tools/pcc-dialog-toolkit/docs/phase6-qa-runbook.md`

## Decision

- Baseline is frozen as `v0.1.0-rc` with OT scope.
- Next milestone: complete LE2 validation and promote to full Phase 6 closure.
