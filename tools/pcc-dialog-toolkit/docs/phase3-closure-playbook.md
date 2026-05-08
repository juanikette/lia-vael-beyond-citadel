# Phase 3 - Closure playbook with real samples

This playbook defines a minimal run to decide whether Phase 3 can move to `Done`.

## 1) Prepare local samples

Place at least 1 file per target profile:

- ME2 OT (for example `samples/me2_ot/*.pcc`)
- LE2 (for example `samples/le2/*.pcc`)

If binaries are not versioned, keep them local only.

## 2) Generate batch reports by profile

```bash
pcc_dialog_extract --phase3-batch-dir samples/me2_ot --phase3-batch-glob "*.pcc" --phase3-batch-report reports/phase3-batch-me2ot.json --pretty
pcc_dialog_extract --phase3-batch-dir samples/le2 --phase3-batch-glob "*.pcc" --phase3-batch-report reports/phase3-batch-le2.json --pretty
```

## 3) Strict per-file gate

For any file with uncertainty:

```bash
pcc_dialog_extract "<path>.pcc" --validate-bioconversation-stubs --strict-validation
```

- Exit code `0`: no blocking validation issues.
- Exit code `3`: `invalid` or `needs_schema_review` is present.

## 4) Minimum closure criteria for Phase 3

- `summary.invalid == 0` on target samples.
- `summary.needs_schema_review == 0`, or only a small residual with a documented mitigation plan.
- `validation_items[].parse_mode` should not be dominated by `count_or_value_fallback` on samples with real BioConversation data.
- No unexplained critical warnings.
- Verification logged in Notion (`Commands`, `Results`, `Remaining risks`).

## 5) If the gate fails

- Review `validation_items` and `row_payloads` from the report.
- Adjust profile schema (`dialogue/schema.py`) or list parser logic.
- If real lists are not exposed as top-level tags, implement nested `StructProperty` parsing (reference: `ConversationExtended.cs` in LegendaryExplorer).
- Repeat runs until behavior is stable.
