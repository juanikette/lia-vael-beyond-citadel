# Phase 5 - Output contract and stable CLI runbook

This runbook validates the Phase 5 goals: resilient extraction flow, versioned JSON output, and stable CLI behavior.

## 1) Run focused tests

```bash
python -m pytest tests/test_phase5_serializer_cli.py tests/test_cli_smoke.py
```

Expected:

- Output serialization tests pass.
- CLI smoke checks pass.

## 2) Generate output JSON from a real sample

```bash
PYTHONPATH=src python -m cli <path_to_sample.pcc> --game me2 --tlk "<path_to_BIOGame_INT.tlk>" --dlc-dir "<path_to_DLC>" --output output.json --pretty
```

Expected:

- Command exits successfully.
- `output.json` is written.
- Console includes warning/error trace lines when present.

## 3) Validate output contract

Confirm output contains:

- `schema_version`
- `tool_version`
- `input`
- `summary`
- `conversations`
- `errors`

And summary consistency:

- `conversations_total == conversations_ok + conversations_failed`
- `conversations_ok == len(conversations)`
- `conversations_failed == len(errors)`

## 4) Resilience behavior checks

- A single conversation parse failure should not abort the full file.
- Failed items must appear under `errors` with identifiers.
- Successful items must still be present under `conversations`.

## 5) Optional batch sanity check

Run multiple files through the same command pattern and compare aggregate totals (ok/failed/warnings).

## Reference notes (from execution log)

- Notion Phase 5 log records successful real-sample runs, contract validation before write, and non-blocking per-conversation error handling.
