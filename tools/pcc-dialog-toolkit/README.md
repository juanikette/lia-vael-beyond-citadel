# pcc-dialog-toolkit

`pcc-dialog-toolkit` is an MVP command-line toolkit for inspecting Mass Effect `.pcc` packages, extracting `BioConversation` dialogue, resolving `StrRef` values through TLK files, and producing narrative evidence reports for mod development.

The current MVP is focused on **Mass Effect 2 Original Trilogy (ME2 OT)** workflows, with additive support for broader OT/LE package parsing where the current reader can safely inspect the data.

## Current Status

- Package version: `0.1.1rc0`
- Evidence report schema: `evidence_schema_version="1.0.0"`
- Primary validated game profile: ME2 OT
- Main production workflow: TLK query -> candidate PCC scan -> evidence report -> regression gate
- Go scanner acceleration: enabled for candidate discovery, StrRef offsets, and container metadata
- Regression harness: available through `scripts/run_probe_regression.py`

## What The Tool Does

- Reads Mass Effect `.pcc` packages.
- Detects `BioConversation` exports.
- Extracts dialogue entries, replies, speakers, node IDs, and `StrRef` values.
- Resolves `StrRef` values through base TLK and DLC TLKs.
- Produces versioned JSON extraction payloads.
- Generates narrative evidence reports for arbitrary dialogue/text queries.
- Uses a Go scanner to accelerate repeated evidence workflows over a full `BioGame` tree.
- Tracks evidence provenance with source tiers:
  - `bioconversation`
  - `semantic_container`
  - `container_fallback`

## Scope And Limitations

- ME2 OT is the validated MVP target.
- LE support is still environment-dependent and should be validated before release claims.
- Full semantic decoding is not yet available for every non-`BioConversation` container.
- Queries with very broad terms such as `liara`, `normandy`, or `quarian` can be expensive and should be run with explicit indexes or tighter query strings.
- Compressed OT PCC files require LZO support:
  - Python path: `lzallright`
  - Go scanner path: `github.com/anchore/go-lzo`

## Repository Layout

```text
tools/pcc-dialog-toolkit/
  src/                         Python CLI and parser modules
  src/cli.py                    Main Python CLI entrypoint
  src/pcc/                      PCC table, export, and property readers
  src/dialogue/                 BioConversation parsing
  src/tlk/                      TLK reading and resolution
  src/serialize/                JSON output contract helpers
  cmd/pcc-scan/                 Go candidate scanner CLI
  internal/scan/                Go scan/index/package helpers
  scripts/run_probe_regression.py
  docs/                         Runbooks and release notes
  tests/                        Python tests
```

## Install For Development

From `tools/pcc-dialog-toolkit/`:

```bash
python -m pip install -e .
python -m pip install -e .[dev]
```

Local non-installed execution is also supported:

```bash
PYTHONPATH=src python -m cli --help
PYTHONPATH=src python -m cli --version
```

On PowerShell, use:

```powershell
$env:PYTHONPATH = "src"
python -m cli --help
```

## Required Game Paths

Most evidence workflows need:

- Base TLK: `.../BioGame/CookedPC/BIOGame_INT.tlk`
- DLC root: `.../BioGame/DLC`
- BioGame root for Go scanner: `.../BioGame`

Example ME2 OT install path:

```text
C:/Program Files/EA Games/Mass Effect 2/BioGame
```

## Core Commands

### List BioConversation Exports

```bash
pcc_dialog_extract "path/to/file.pcc" --list-bioconversations
```

### Dump BioConversation Stubs

```bash
pcc_dialog_extract "path/to/file.pcc" --dump-bioconversation-stub --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC" --pretty
```

This prints normalized conversation rows with entries, replies, speakers, `StrRef` IDs, and resolved text where available.

### Validate BioConversation Stubs

```bash
pcc_dialog_extract "path/to/file.pcc" --validate-bioconversation-stubs --strict-validation --pretty
```

Use this as a strict parser gate for known-good BioConversation samples.

### Export Normalized JSON

```bash
pcc_dialog_extract "path/to/file.pcc" --game me2 --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC" --output output.json --pretty
```

The output payload includes:

- `schema_version`
- `tool_version`
- `input`
- `summary`
- `conversations`
- `errors`

## TLK Search And StrRef Tracing

### Search TLK Text

```bash
pcc_dialog_extract "path/to/file.pcc" --scan-tlk-reference "rally the crowd" --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC"
```

### Trace Specific StrRefs In BioConversation Nodes

```bash
pcc_dialog_extract "path/to/file.pcc" --trace-strref-usage 282425 --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC"
```

This is useful when you already know the TLK `StrRef` and want to confirm whether a parsed `BioConversation` node references it.

## Evidence Reports

Evidence reports search TLK content first, resolve matching `StrRef` IDs, scan candidate PCC files, and report where those strings are likely used.

### Auto Go Index Mode

```bash
pcc_dialog_extract --evidence-report reports/probe_rally.json --evidence-query "rally the crowd" --tlk "C:/Program Files/EA Games/Mass Effect 2/BioGame/CookedPC/BIOGame_INT.tlk" --dlc-dir "C:/Program Files/EA Games/Mass Effect 2/BioGame/DLC" --pretty
```

When `--candidate-index` is omitted, the CLI attempts to run the Go scanner automatically. If Go is unavailable, it falls back to the Python prefilter path.

### Explicit Candidate Index Mode

First build an index:

```bash
go run ./cmd/pcc-scan --root-biogame "C:/Program Files/EA Games/Mass Effect 2/BioGame" --strref 282425 --out reports/candidates_rally.json
```

Then use it:

```bash
pcc_dialog_extract --evidence-report reports/probe_rally.json --evidence-query "rally the crowd" --candidate-index reports/candidates_rally.json --tlk "C:/Program Files/EA Games/Mass Effect 2/BioGame/CookedPC/BIOGame_INT.tlk" --dlc-dir "C:/Program Files/EA Games/Mass Effect 2/BioGame/DLC" --pretty
```

Explicit indexes are recommended for repeated runs because they avoid rebuilding the candidate set.

## Evidence Report Contract

Evidence reports include:

- `report`: currently `dialogue-evidence`
- `evidence_schema_version`: currently `1.0.0`
- `queries`: normalized query list
- `summary`: counts, source selection, errors, and timing
- `tlk_hits`: matching TLK rows
- `strref_usages`: selected highest-priority usage rows
- `raw_export_hits`: low-level export/offset evidence
- `container_hits`: normalized raw hit rows
- `semantic_container_usages`: semantic or class-hinted non-BioConversation rows
- `non_bioconversation_usages`: fallback rows outside parsed BioConversation hits
- `errors`: stage-scoped errors

Important summary fields:

- `summary.strref_usage_source`: selected tier (`bioconversation`, `semantic_container`, or `container_fallback`)
- `summary.candidate_source`: `go_auto_index`, `index`, or `python_prefilter`
- `summary.index_container_files`: candidate files with enriched Go container metadata
- `summary.index_offset_files`: candidate files with raw StrRef offset metadata
- `summary.timing_ms`: `tlk_scan`, `candidate_selection`, `candidate_parse`, and `total`

## Evidence Source Tiers

The report selects the best available source in this order:

1. `bioconversation`
2. `semantic_container`
3. `container_fallback`

`bioconversation` means a parsed BioConversation entry/reply node directly references the target `StrRef`.

`semantic_container` means the target was promoted from a recognized semantic/container context, such as sequence dialogue class hints or parsed property-level evidence.

`container_fallback` means the target `StrRef` signature was found in a package/export container, but a more precise semantic parser has not yet decoded that structure.

## Go Candidate Scanner

The Go scanner is optimized for repeated full-tree evidence runs.

Cold scan:

```bash
go run ./cmd/pcc-scan --root-biogame "C:/Program Files/EA Games/Mass Effect 2/BioGame" --strref 282425 --out reports/candidates_rally.json
```

Warm incremental scan:

```bash
go run ./cmd/pcc-scan --root-biogame "C:/Program Files/EA Games/Mass Effect 2/BioGame" --index reports/candidates_rally.json --strref 282425 --out reports/candidates_rally.json
```

The index includes:

- `capabilities`
- `candidates`
- `hits_by_file`
- `offsets_by_file`
- `containers_by_file`
- `container_status_by_file`
- `container_status_counts`
- `entries`

`container_status_counts` helps diagnose why a candidate did or did not receive enriched container metadata.

## Regression Harness

Run the Phase 12/13 probe gate:

```bash
python scripts/run_probe_regression.py --tlk "C:/Program Files/EA Games/Mass Effect 2/BioGame/CookedPC/BIOGame_INT.tlk" --dlc-dir "C:/Program Files/EA Games/Mass Effect 2/BioGame/DLC" --out-dir reports
```

The harness checks:

- each probe has `tlk_hits > 0`
- each probe has `raw_export_hits > 0`
- each probe has `candidate_pcc_files > 0`
- `evidence_schema_version == "1.0.0"`
- at least one probe reports `strref_usage_source="semantic_container"`

Current MVP baseline:

- Tali intimacy: fallback evidence expected
- Miss vas Normandy: fallback evidence expected
- Rally the crowd: semantic container evidence expected

## Recommended QA Commands

Run all Python tests:

```bash
python -m pytest
```

Run Go scanner tests:

```bash
go test ./...
```

Run the evidence regression harness:

```bash
python scripts/run_probe_regression.py --tlk "C:/Program Files/EA Games/Mass Effect 2/BioGame/CookedPC/BIOGame_INT.tlk" --dlc-dir "C:/Program Files/EA Games/Mass Effect 2/BioGame/DLC" --out-dir reports
```

Run a strict BioConversation validation sample:

```bash
pcc_dialog_extract "C:/Program Files/EA Games/Mass Effect 2/BioGame/CookedPC/BioD_Nor_350Henchmen_LOC_INT.pcc" --validate-bioconversation-stubs --strict-validation --pretty
```

## Query Design Guidance

Use phrase-level queries for normal MVP operation:

- Good: `rally the crowd`
- Good: `miss vas normandy`
- Good: `middle of some calibrations`
- Good: `dalliance attractive as stress release`

Avoid very broad single-token queries unless you have a strict timeout or prebuilt index:

- Expensive: `liara`
- Expensive: `normandy`
- Expensive: `quarian`
- Expensive: `collector`

Broad queries can match hundreds of TLK rows and produce thousands of raw export hits.

## Troubleshooting

### `Base TLK does not exist`

Verify `--tlk` points to the base runtime TLK:

```text
.../BioGame/CookedPC/BIOGame_INT.tlk
```

### `DLC directory does not exist`

Verify `--dlc-dir` points to:

```text
.../BioGame/DLC
```

### `Candidate index does not exist`

Regenerate the index with `go run ./cmd/pcc-scan` or fix the `--candidate-index` path.

### `Candidate index must contain a 'candidates' array`

The supplied JSON is not a valid candidate index. Regenerate it with the Go scanner.

### `go_auto_index_failed` or `go_auto_index_error`

Run the Go scanner manually:

```bash
go run ./cmd/pcc-scan --root-biogame ".../BioGame" --strref 282425 --out reports/candidates_debug.json
```

Also verify:

```bash
go test ./...
```

## Current Validation Snapshot

Recent intensive validation covered:

- malformed candidate index through full CLI: clean `EXIT_CODE=2`, no traceback
- missing candidate index path: clean `EXIT_CODE=2`
- full Python tests: `57 passed`
- Go tests: pass
- regression harness: pass
- Go cold/warm index scans: pass
- BioConversation tree extraction checks on `nor_engineers_a_dlg`: pass
- broad query timeout behavior: confirmed, requires operational guardrails

## Runbooks And Release Notes

- `docs/phase0-setup-checklist.md` - environment/bootstrap checklist.
- `docs/phase1-pcc-reader-smoke.md` - basic PCC header/table reader verification.
- `docs/phase2-bioconversation-detection.md` - BioConversation detection verification.
- `docs/phase3-closure-playbook.md` - closure gate for semantic parsing quality.
- `docs/phase4-validation-runbook.md` - TLK resolution validation with DLC precedence.
- `docs/phase5-output-contract-runbook.md` - output schema and resilient CLI contract checks.
- `docs/phase6-qa-runbook.md` - OT/LE QA execution and LEX cross-check workflow.
- `docs/phase13-mvp-runbook.md` - production command flow, regression gate, and troubleshooting.
- `docs/output-schema-v0.1.md` - JSON contract reference.
- `docs/legendaryexplorer-reference-map.md` - LegendaryExplorer reference mapping by phase.
- `docs/release-v0.1.0-rc.md` - Phase 6 OT baseline release candidate notes.
- `docs/release-v0.1.1-rc-phase13.md` - current MVP hardening release candidate notes.
