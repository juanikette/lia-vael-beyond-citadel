# Phase 6 - QA with OT/LE samples and LEX validation

Goal: validate the MVP (`schema_version=0.1`) with reproducible evidence on ME2 OT and LE2, comparing targeted results against the LegendaryExplorer (LEX) baseline.

## Operational plan

1. Prepare a fixed sample corpus per profile (`OT` and `LE2`).
2. Run versioned JSON extraction per sample with base TLK + DLC.
3. Consolidate health metrics (`ok/failed/warnings`) for each run.
4. Verify control lines (`StrRef`, `line_text`, links, speaker tags) against LEX.
5. Log non-blocking issues and decide `v0.1.0` freeze readiness.

## Prerequisites

- `python` with the toolkit environment active.
- `lzallright` installed for compressed OT PCC files.
- Valid local paths to:
  - ME2 OT (`BioGame/CookedPC`, `BIOGame_INT.tlk`, `BioGame/DLC`)
  - LE2 (`Game/ME2/BioGame/CookedPCConsole`, `BIOGame_INT.tlk`, `DLC`)

## Suggested samples

Use at least 3 PCC files per profile. If available, prefer 5 for better coverage.

- Recommended OT:
  - `BioD_CitHub_LOC_INT.pcc`
  - `BioD_CitHub_300Dialogue_LOC_INT.pcc`
  - `BioD_CitHub_230Baily_LOC_INT.pcc`
  - `BioD_CitAsL_LOC_INT.pcc`
  - `BioD_CitGrL_300MeetTheMole_LOC_INT.pcc`
- Recommended LE2:
  - mirror filenames when available in `CookedPCConsole`
  - otherwise choose 3-5 `BioD_*LOC_INT.pcc` files containing `BioConversation`

## Base command per sample

```bash
pcc_dialog_extract <pcc_path> --game <me2|le2> --tlk "<BIOGame_INT.tlk_path>" --dlc-dir "<dlc_path>" --output "<output_json>" --pretty
```

## Minimum evidence per sample

- `summary.conversations_total`, `summary.conversations_failed`, `summary.warnings_total`.
- 3-5 control lines with:
  - `conversation_id`
  - `entry_id` or `reply_id`
  - `line_strref`
  - `line_text`
- Resilient-parse status:
  - `errors[]` empty, or explicit failures with `export_index`.

## LEX validation checklist

For each control line:

1. Open the equivalent conversation in LEX.
2. Confirm `StrRef` matches.
3. Confirm resolved text (`line_text`) matches effective LEX/TLK output.
4. Confirm link consistency (`reply_links`, `target_entry_id`) and speaker tags.
5. Log `OK` or `Mismatch` with details.

## Phase 6 pass criteria

- OT: target corpus runs without crashes and without critical failures.
- LE2: target corpus runs without crashes and without critical failures.
- Targeted LEX validation completed on both profiles.
- Remaining issues classified as non-blocking for `v0.1.0`.

## Contingency if no local LE2 installation is available

If a local LE2 installation is unavailable, apply a controlled partial closure:

- Run expanded OT QA (>=25 `BioD_*LOC_INT.pcc` samples) to increase confidence.
- Keep targeted LEX comparison for OT control lines.
- Mark LE2 validation as `environment pending` in Notion.
- Do not mark OT/LE coverage as complete; keep `v0.1.0-rc` status (OT validated, LE2 deferred).

## Recommended outputs

- Per-sample JSON in `tools/pcc-dialog-toolkit/output/phase6-<profile>/`.
- Consolidated report per profile (`phase6-ot-report.json`, `phase6-le2-report.json`).
- Closure note in Notion (`Phase 6 - MVP QA`).
