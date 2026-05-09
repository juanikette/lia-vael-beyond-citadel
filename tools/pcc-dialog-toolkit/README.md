# pcc-dialog-toolkit

MVP toolkit for extracting `BioConversation` dialogue from Mass Effect `.pcc` files (OT/LE).

## Code structure

- Source code lives directly in `src/` (no `src/pcc_dialog_toolkit/` subpackage).
- Main modules:
  - `src/cli.py`
  - `src/pcc/`
  - `src/dialogue/`
  - `src/tlk/`
  - `src/serialize/`
  - `src/model/`

## What the tool does

- Reads Mass Effect `.pcc` packages and detects `BioConversation` exports.
- Extracts dialogue stubs (`entries`, `replies`, `speakers`) as JSON.
- Resolves `StrRef` values using a base TLK and optional DLC overrides.
- Produces versioned JSON output with warning and error summaries.
- Supports strict validation so the CLI can be used as an automated gate.

## Scope and limitations

- Supports OT/LE profiles focused on `BioConversation` parsing.
- Requires `lzallright` for compressed OT PCC files (LZO).
- In resilient mode, per-conversation failures are reported without aborting the full file.
- Unknown profile/schema mismatches are flagged with `needs_schema_review`.

## Usage

```bash
pcc_dialog_extract path/to/file.pcc --list-bioconversations
pcc_dialog_extract path/to/file.pcc --inspect-bioconversation-properties
pcc_dialog_extract path/to/file.pcc --inspect-bioconversation-owners
pcc_dialog_extract path/to/file.pcc --find-reference "Lia'Vael" --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC"
pcc_dialog_extract path/to/file.pcc --find-context-profile lia-vael --context-min-score 4 --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC"
pcc_dialog_extract path/to/file.pcc --scan-tlk-reference "Lia'Vael" --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC"
pcc_dialog_extract path/to/file.pcc --trace-strref-usage 253865 --trace-strref-usage 260225 --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC"
pcc_dialog_extract --lia-vael-evidence-report reports/lia-vael-evidence.json --tlk ".../CookedPC/BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC" --pretty
pcc_dialog_extract --evidence-report reports/custom-evidence.json --evidence-query "tali'zorah" --evidence-query "rally the crowd" --tlk ".../CookedPC/BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC" --pretty
pcc_dialog_extract --evidence-report reports/custom-evidence.json --evidence-query "rally the crowd" --candidate-index reports/candidates.json --tlk ".../CookedPC/BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC" --pretty
pcc_dialog_extract path/to/file.pcc --dump-bioconversation-stub --pretty
pcc_dialog_extract path/to/file.pcc --dump-bioconversation-row-payloads --pretty
pcc_dialog_extract path/to/file.pcc --validate-bioconversation-stubs --pretty
pcc_dialog_extract path/to/file.pcc --validate-bioconversation-stubs --strict-validation
pcc_dialog_extract path/to/file.pcc --phase3-report reports/phase3-sample.json --pretty
pcc_dialog_extract --phase3-batch-dir samples/me2_ot --phase3-batch-glob "*.pcc" --phase3-batch-report reports/phase3-batch-me2ot.json --pretty
pcc_dialog_extract path/to/file.pcc --dump-bioconversation-stub --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC" --pretty
pcc_dialog_extract path/to/file.pcc --game me2 --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC" --output output.json --pretty
```

For local development without installing the script (from `tools/pcc-dialog-toolkit/`):

```bash
PYTHONPATH=src python -m cli --help
PYTHONPATH=src python -m cli --version
```

When `--dump-bioconversation-stub` is used with `--tlk`, the CLI resolves `line_text` for `EntryNode` and `ReplyNode`.
When `--dlc-dir` is provided, DLC TLKs are loaded by priority (`MountPriority`) and may override base TLK strings.
By default, the resolver ignores test TLKs (`*_Test_INT.tlk`) to prioritize runtime content.

When `--output` is used, the CLI writes versioned output (`schema_version`) that includes:

- successfully parsed `conversations`
- per-conversation `errors` (without aborting the full file)
- aggregate `summary` counts and warning totals

The CLI validates a minimal output contract before writing files (required top-level fields and consistent summary counts).
If warnings or conversation-level errors are present, it also prints them to the console for immediate traceability.

`--validate-bioconversation-stubs` marks `needs_schema_review=true` when the profile is unknown or parsing suggests a schema mismatch.

`--scan-tlk-reference` searches raw TLK content (base + DLC) for one or more substrings and prints matching `StrRef` IDs.

`--trace-strref-usage` scans parsed BioConversation stubs and reports where target `StrRef` IDs appear (entry/reply node + conversation id).

`--lia-vael-evidence-report` runs a single consolidated sweep: it finds Lia'Vael-related TLK strings first, then traces those `StrRef` IDs across all base + DLC `.pcc` conversation stubs and writes one JSON report.

`--evidence-report` is the generalized variant: provide one or more `--evidence-query` values and it generates the same consolidated TLK + StrRef usage report for any narrative target.

Evidence reports include tiered linkage sections:
- `strref_usages`: highest-priority usage rows selected from parsed `BioConversation`, semantic container parsing, or raw container fallback.
- `semantic_container_usages`: hits recovered from parsed `StringRefProperty` tags when a non-`BioConversation` export exposes the target as a property.
- `non_bioconversation_usages`: raw container fallback rows for target `StrRef` signatures outside parsed `BioConversation` nodes.
- `raw_export_hits`: low-level export/offset evidence. When the Go candidate index includes `offsets_by_file`, Python maps those offsets to the smallest containing export instead of rescanning every export payload.

`summary.strref_usage_source` records the selected tier (`bioconversation`, `semantic_container`, or `container_fallback`). Phase 9 uses LegendaryExplorer references for property semantics, especially `PropertyReader.cs` (`StringRefProperty`) and `ConversationScanner.cs` (`BioConversation` `srText` extraction), while keeping the current raw fallback explicit for containers that are not yet semantically decoded.

For performance, evidence reports first prefilter candidate `.pcc` files by raw `StrRef` binary signatures before running package-level parsing.

Optional hybrid mode (Go scanner):

```bash
go run ./cmd/pcc-scan --root-biogame ".../BioGame" --strref 282425 --strref 302426 --out reports/candidates.json
go run ./cmd/pcc-scan --root-biogame ".../BioGame" --index reports/candidates.json --strref 282425 --strref 302426 --out reports/candidates.json
```

Then pass that index to Python evidence extraction with `--candidate-index`.

The `--index` flag enables incremental refresh: unchanged files are reused from existing index entries, and only changed/new files are rescanned.

When `--candidate-index` is omitted, the CLI attempts to auto-run the Go scanner first (`go run ./cmd/pcc-scan`) and falls back to the Python prefilter path if Go is unavailable.

Evidence report summaries include `timing_ms` for `tlk_scan`, `candidate_selection`, `candidate_parse`, and `total`.

Evidence reports now include `evidence_schema_version` (current: `1.0.0`) for contract stability checks.

Phase 12 regression harness (runs all 3 narrative probes and enforces gates):

```bash
python scripts/run_probe_regression.py --tlk "C:/Program Files/EA Games/Mass Effect 2/BioGame/CookedPC/BIOGame_INT.tlk" --dlc-dir "C:/Program Files/EA Games/Mass Effect 2/BioGame/DLC" --out-dir reports
```

## Verification snapshot

- Full Python test suite:
  - `python -m pytest`
  - Expected: all tests pass.
- Go scanner build/check:
  - `go test ./...`
  - Expected: scanner package resolves and reports no failing tests.
- Hybrid evidence smoke examples (auto Go index path):
  - `python -m cli --evidence-report <out1.json> --evidence-query "dalliance attractive as stress release" --evidence-query "self-sterilize" --evidence-query "oral contact with tissue dangerous" --tlk <BIOGame_INT.tlk> --dlc-dir <BioGame/DLC> --pretty`
  - `python -m cli --evidence-report <out2.json> --evidence-query "miss vas normandy" --tlk <BIOGame_INT.tlk> --dlc-dir <BioGame/DLC> --pretty`
  - `python -m cli --evidence-report <out3.json> --evidence-query "rally the crowd" --tlk <BIOGame_INT.tlk> --dlc-dir <BioGame/DLC> --pretty`
  - Expected summary fields include `candidate_source="go_auto_index"` and `timing_ms`.

## JSON output (summary)

`--output` includes:

- `schema_version`
- `tool_version`
- `input`
- `summary`
- `conversations`
- `errors`

## Runbooks index

- `docs/phase0-setup-checklist.md` - environment/bootstrap checklist.
- `docs/phase1-pcc-reader-smoke.md` - basic PCC header/table reader verification.
- `docs/phase2-bioconversation-detection.md` - BioConversation detection verification.
- `docs/phase3-closure-playbook.md` - closure gate for semantic parsing quality.
- `docs/phase4-validation-runbook.md` - TLK resolution validation with DLC precedence.
- `docs/phase5-output-contract-runbook.md` - output schema and resilient CLI contract checks.
- `docs/phase6-qa-runbook.md` - OT/LE QA execution and LEX cross-check workflow.
- `docs/phase13-mvp-runbook.md` - production command flow, regression gate, and troubleshooting.
- `docs/output-schema-v0.1.md` - JSON contract reference.
- `docs/legendaryexplorer-reference-map.md` - LEX reference mapping by phase.
- `docs/release-v0.1.0-rc.md` - current RC release notes.
- `docs/release-v0.1.1-rc-phase13.md` - MVP hardening RC notes.
