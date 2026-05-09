# pcc-dialog-toolkit v0.1.1-rc (Phase 13 MVP hardening)

Date: 2026-05-09

Release status: MVP release candidate (ME2 OT focused) with hardened evidence workflow.

## Summary

- Added production runbook for index, evidence generation, and regression execution.
- Added explicit evidence contract marker: `evidence_schema_version="1.0.0"`.
- Added reusable probe regression harness for the 3 narrative probes.
- Improved Go container mapping coverage on compressed candidates with diagnostic status reporting.

## Validation snapshot

- Go tests: `go test ./...` -> pass.
- Python smoke tests: `python -m pytest tests/test_cli_smoke.py -q` -> pass.
- Regression harness: `python scripts/run_probe_regression.py ...` -> pass.

Probe regression summary (latest run):
- `tali_intimacy`: `strref_usage_source=container_fallback`, `tlk_hits=2`, `raw_export_hits=44`.
- `miss_vas_normandy`: `strref_usage_source=container_fallback`, `tlk_hits=2`, `raw_export_hits=12`.
- `rally_the_crowd`: `strref_usage_source=semantic_container`, `semantic_container_usages=20`, `tlk_hits=1`, `raw_export_hits=86`.

## Included hardening changes

- `tools/pcc-dialog-toolkit/scripts/run_probe_regression.py`
  - Executes all 3 probes.
  - Enforces schema and minimum evidence gates.
  - Fails fast on regressions.
- `tools/pcc-dialog-toolkit/docs/phase13-mvp-runbook.md`
  - Documents production command flow and troubleshooting.
- Evidence report output now includes:
  - `evidence_schema_version`.
- Go candidate index now includes container mapping diagnostics:
  - `container_status_by_file`
  - `container_status_counts`

## Known limitations

- Semantic container promotion is currently validated on Rally baseline; other probes still resolve through fallback tiers.
- LE2 execution remains pending environment availability.

## Decision

- Accept as MVP RC for OT-focused narrative evidence workflows.
- Continue semantic expansion for remaining probes while keeping contract and harness stable.
