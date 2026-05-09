# Phase 13 MVP Runbook

This runbook defines the production-facing command flow for the current MVP state.

## 1) Build or refresh candidate index (Go)

```bash
go run ./cmd/pcc-scan --root-biogame "C:/Program Files/EA Games/Mass Effect 2/BioGame" --strref 282425 --out reports/candidates_rally.json
```

Incremental refresh mode:

```bash
go run ./cmd/pcc-scan --root-biogame "C:/Program Files/EA Games/Mass Effect 2/BioGame" --index reports/candidates_rally.json --strref 282425 --out reports/candidates_rally.json
```

Expected outcome:
- `candidate index written: ...`
- `files_scanned=... reused=... rescanned=... candidates=... errors=...`

## 2) Generate evidence report (Python)

With explicit candidate index:

```bash
python -m cli --evidence-report reports/probe_rally.json --evidence-query "rally the crowd" --candidate-index reports/candidates_rally.json --tlk "C:/Program Files/EA Games/Mass Effect 2/BioGame/CookedPC/BIOGame_INT.tlk" --dlc-dir "C:/Program Files/EA Games/Mass Effect 2/BioGame/DLC" --pretty
```

Auto-index mode:

```bash
python -m cli --evidence-report reports/probe_rally.json --evidence-query "rally the crowd" --tlk "C:/Program Files/EA Games/Mass Effect 2/BioGame/CookedPC/BIOGame_INT.tlk" --dlc-dir "C:/Program Files/EA Games/Mass Effect 2/BioGame/DLC" --pretty
```

Expected summary fields:
- `evidence_schema_version` (current `1.0.0`)
- `summary.candidate_source`
- `summary.strref_usage_source`
- `summary.timing_ms`

## 3) Run full probe regression gate

```bash
python scripts/run_probe_regression.py --tlk "C:/Program Files/EA Games/Mass Effect 2/BioGame/CookedPC/BIOGame_INT.tlk" --dlc-dir "C:/Program Files/EA Games/Mass Effect 2/BioGame/DLC" --out-dir reports
```

Gate expectations:
- each probe has `tlk_hits > 0`
- each probe has `raw_export_hits > 0`
- `evidence_schema_version == "1.0.0"`
- at least one probe reports `strref_usage_source="semantic_container"`

## 4) Troubleshooting

- **`Base TLK does not exist`**
  - verify `--tlk` points to `.../BioGame/CookedPC/BIOGame_INT.tlk`
- **`DLC directory does not exist`**
  - verify `--dlc-dir` points to `.../BioGame/DLC`
- **`go_auto_index_failed` / `go_auto_index_error`**
  - run `go test ./...`
  - run `go run ./cmd/pcc-scan ...` manually to confirm scanner path
- **`candidate index must contain a 'candidates' array`**
  - regenerate index with `go run ./cmd/pcc-scan`

## 5) Current limitations

- Semantic container promotion is currently validated on Rally baseline and still expanding to other narrative probes.
- Non-target classes may still resolve via fallback tiers when semantic parsers are not yet implemented.
