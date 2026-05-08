# Phase 1 - PCC reader smoke runbook

This runbook validates basic PCC package reading: header, names, imports, and exports.

## 1) Basic test validation

Run Phase 1 tests:

```bash
python -m pytest tests/test_pcc_reader_phase1.py
```

Expected:

- PCC header/table parsing tests pass.
- Invalid-file scenarios raise controlled `PccFormatError` paths.

## 2) CLI smoke against a sample PCC

Use any known valid sample:

```bash
PYTHONPATH=src python -m cli <path_to_sample.pcc>
```

Expected console sections:

- `PCC: ...`
- `Header: unreal=... licensee=...`
- `Tables: names=... imports=... exports=...`

## 3) Regression check (full suite)

```bash
python -m pytest
```

Expected:

- Full suite remains green after reader changes.

## 4) Troubleshooting

- If parsing fails immediately, verify the file is a valid ME package (`.pcc`) and not truncated.
- If offsets are out of range, test with another sample to rule out local file corruption.
- If compression is involved (ME2 OT), ensure `lzallright` is installed.

## Reference notes (from execution log)

- Notion Phase 1 log confirms defensive parser coverage for header/names/imports/exports and successful CLI inspection behavior.
