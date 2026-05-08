# Phase 2 - BioConversation detection runbook

This runbook validates reliable detection and listing of `BioConversation` exports.

## 1) Run focused tests

```bash
python -m pytest tests/test_phase2_bioconversation_detection.py
```

Expected:

- Detection tests pass for synthetic coverage.
- CLI listing behavior is validated.

## 2) Run CLI listing on a real PCC sample

```bash
PYTHONPATH=src python -m cli <path_to_sample.pcc> --list-bioconversations
```

Expected output pattern:

- `BioConversation exports: <n>`
- Per item: `idx`, `name`, `class`, `offset`, `size`

## 3) Practical acceptance checks

- At least one known conversation package reports non-zero `BioConversation` count.
- Reported class is `BioConversation` for listed rows.
- Offsets and sizes are non-negative and plausible.

## 4) Troubleshooting

- If count is `0` on expected files, verify the sample is a localized/dialogue package (for example `BioD_*LOC_INT.pcc`).
- If class resolution looks wrong, re-run full tests to verify import/export mapping regressions.

## Reference notes (from execution log)

- Notion Phase 2 log records the `--list-bioconversations` workflow as the primary deliverable and confirms metadata fields (`name`, `index`, `class`, `offset`, `size`).
