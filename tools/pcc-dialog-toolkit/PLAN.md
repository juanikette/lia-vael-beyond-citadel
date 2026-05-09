# Implementation plan - Mass Effect dialogue toolkit (OT/LE)

## Tool name

Selected name: **pcc-dialog-toolkit**

## External knowledge source (required)

Reference repository for process and technical validation:

- https://github.com/ME3Tweaks/LegendaryExplorer/

Usage rule during implementation:

- Consult LegendaryExplorer before closing each phase that touches PCC/TLK parsing.
- Prioritize naming, read order, and behavior observable in mature tools.
- Do not copy code blindly: use it as a guide for format details, edge cases, and verification.
- Record in phase notes which LegendaryExplorer files/classes were used as references.

## MVP goal

Implement a CLI named `pcc_dialog_extract` that:

1. Reads a ME OT/LE `.pcc` file.
2. Detects `BioConversation` exports.
3. Extracts nodes, replies, speakers, and `StrRef`.
4. Resolves text via TLK (`BIOGame_INT.tlk` + DLC TLKs).
5. Exports the result to `output.json`.

## Scope and limits

### Includes
- Partial package-format parsing (relevant names/imports/exports/properties).
- Parsing of structures required for conversations.
- `StrRef -> text` resolution.
- Stable and versioned JSON output.

### Excludes (MVP)
- Rendering, meshes, textures, shaders.
- Visual editing.
- Advanced FaceFX/Wwise.
- Full binary reinjection (designed in a later phase).

## Recommended stack

- **MVP**: Python 3.11+
- `typer` or `argparse` for CLI
- `pydantic` (optional) for AST/JSON output validation
- Tests with `pytest`

Reason: high iteration speed for validating data format and end-to-end flow.

## Proposed architecture

```text
input.pcc
  -> pcc_reader
  -> export_scanner (BioConversation)
  -> conversation_parser
  -> tlk_resolver
  -> serializer_json
  -> output.json
```

Suggested modules:

- `src/cli.py`
- `src/pcc/reader.py`
- `src/pcc/tables.py`
- `src/pcc/properties.py`
- `src/dialogue/conversation_parser.py`
- `src/tlk/reader.py`
- `src/tlk/resolver.py`
- `src/model/ast.py`
- `src/serialize/json_writer.py`

## AST model v0.1

### Conversation
- `id`: string (object name)
- `export_index`: int
- `package_path`: string
- `entries`: `EntryNode[]`
- `replies`: `ReplyNode[]`
- `speakers`: `Speaker[]`

### EntryNode
- `id`: int
- `speaker_id`: int|null
- `speaker_tag`: string|null
- `listener_tag`: string|null
- `line_strref`: int|null
- `line_text`: string|null
- `reply_links`: int[]

### ReplyNode
- `id`: int
- `line_strref`: int|null
- `line_text`: string|null
- `target_entry_id`: int|null
- `condition_refs`: string[]

### Speaker
- `id`: int
- `tag`: string|null
- `display_name`: string|null

## Target CLI (phase 1)

```bash
pcc_dialog_extract input.pcc \
  --game me2 \
  --tlk ".../BIOGame_INT.tlk" \
  --dlc-dir ".../BioGame/DLC" \
  -o output.json
```

Minimum flags:
- `--game`: `me1|me2|me3|le1|le2|le3`
- `--tlk`: base TLK path
- `--dlc-dir`: DLC folder (optional)
- `-o, --output`: output JSON file
- `--pretty`: human-readable JSON

## Phase plan

### Phase 0 - Repository setup
- Create folder structure.
- Define output JSON format v0.1.
- Add test cases with 1-2 known real PCC files.

### Phase 1 - Basic package reading
- Implement header + names/imports/exports table reader.
- Expose API to iterate exports by class/name.
- Verify reading across several OT/LE PCC files.

### Phase 2 - BioConversation detection
- Identify exports with class `BioConversation`.
- Dump minimal metadata (name, index, class, offset, size).

### Phase 3 - Conversation parsing
- Parse key properties/lists (EntryList/ReplyList/SpeakerList).
- Resolve links between nodes.
- Build normalized AST.

### Phase 4 - TLK resolver
- Implement base TLK reader.
- Resolve AST `StrRef` values.
- Load DLC TLKs and apply priority/override.

### Phase 5 - Stable serializer and CLI
- Export final JSON with versioned schema.
- Per-conversation error handling (do not abort entire file).
- Warning logs for unparsed fields.

### Phase 6 - MVP QA
- Validate output against ME2 OT and LE2 samples.
- Compare selected lines against in-game/LEX results.
- Freeze extractor `v0.1.0`.

### Phase 7 - Reference tracing and narrative evidence
- Add CLI support to search TLK catalogs directly for narrative references (`--scan-tlk-reference`).
- Add CLI support to trace target `StrRef` IDs back to parsed conversation nodes (`--trace-strref-usage`).
- Add contextual profile scanning for indirect references when explicit names are absent (`--find-context-profile lia-vael`).
- Produce reproducible evidence reports separating:
  - direct-name hits,
  - contextual hits,
  - TLK-only references with no conversation linkage.

### Phase 8 - Container coverage expansion for conversation linkage
- Identify the container/path where TLK-backed narrative lines are linked outside the current `BioConversation` extraction subset.
- Add parser support for additional conversation-bearing structures discovered in ME2 OT/LE packages.
- Extend extraction to surface linkage evidence for lines currently reported as `TLK-only`.
- Add targeted regression probes for:
  - Tali romance/intimacy sequence context,
  - Liara/Shepard cabin exchange ("Miss vas Normandy" reference chain),
  - Tali trial prompt branch (`[Rally the crowd]`).
- Keep outputs additive and traceable, preserving current JSON contract while introducing explicit parse-mode/source markers for newly covered containers.

### Phase 9 - Semantic non-BioConversation linkage and evidence hardening
- Start every implementation block by consulting LegendaryExplorer references for the targeted container/parsing path, and record the exact files/classes reviewed in phase notes.
- Select the first validated non-`BioConversation` container with stable probe coverage and define a minimal semantic extraction contract:
  - `strref`,
  - `source_container` metadata,
  - contextual path fields needed to replace raw-offset-only linkage.
- Implement the first semantic parser for that container in Python and promote semantic hits ahead of raw signature hits in report assembly.
- Keep current raw signature container fallback additive and explicit, but prefer usage tiers in this order:
  - `bioconversation`,
  - `semantic_container`,
  - `container_fallback`.
- Introduce evidence ranking/provenance markers (`strref_usage_source`, optional confidence/tier fields) to reduce noise and make narrative validation actionable.
- Re-run and compare the three narrative probes with regression gates on:
  - non-zero linkage,
  - semantic-hit count,
  - parity of TLK discovery,
  - bounded fallback-only noise.
- Expand unit coverage for parser and report-priority behavior, including source precedence tests.
- Update README and Notion phase log with:
  - LegendaryExplorer references consulted,
  - before/after probe metrics,
  - remaining gaps for next container onboarding.

### Phase 10 - Go-first evidence acceleration and enriched candidate indexes
- Consult LegendaryExplorer package/export references before porting PCC table parsing, especially `LegendaryExplorerCore/Packages/ExportEntry.cs` and package table readers used to populate export metadata.
- Move high-volume binary work from Python to Go while keeping Python as report orchestrator:
  - TLK substring scan candidate discovery,
  - PCC export table parsing,
  - absolute StrRef offset to export-container mapping,
  - noise filtering/ranking for raw fallback containers.
- Extend Go scanner index contract with explicit capabilities so old indexes can be invalidated safely instead of reused without required data.
- Emit enriched container rows from Go where possible:
  - `file`,
  - `strref`,
  - `absolute_offset`,
  - `export_index`,
  - `export_name`,
  - `class_name`,
  - `local_offset`.
- Optimize Go scanner internals for repeated evidence workflows:
  - native byte search instead of manual byte loops,
  - bounded offsets per target,
  - incremental refresh keyed by file identity and index capabilities.
- Add Go-side PCC decompression for ME2 OT compressed candidate packages:
  - use `github.com/anchore/go-lzo` as the preferred LZO1X dependency candidate (permissive README, block `Decompress(src, dst)` API),
  - do not use `github.com/rasky/go-lzo` because its README declares GPLv2 licensing,
  - keep `github.com/pierrec/lz4` noted only for future profiles/packages that actually use LZ4, not for the current ME2 OT LZO path.
- Mirror LegendaryExplorer's compressed-package flow from `LegendaryExplorerCore/Packages/CompressionHelper.cs`:
  - locate compression info,
  - read chunk table,
  - validate chunk headers and block headers,
  - decompress each block into the expected uncompressed size,
  - reconstruct the package buffer before name/import/export parsing.
- Update Python evidence flow to prefer enriched Go index data and avoid opening PCC files unless BioConversation parsing is explicitly needed.
- Add regression measurements for the three narrative probes comparing:
  - Go index build/refresh time,
  - Python candidate parse time,
  - output parity and fallback noise count.

### Phase 11 - First production semantic container parser
- Use Phase 10 enriched offsets/container metadata to identify the first inner serialized structure that actually owns the target `StrRef` values.
- Consult and record LegendaryExplorer references before implementation, prioritizing:
  - Kismet/sequence object parsing,
  - property readers for nested structs/arrays,
  - any dialogue dumper or asset database scanner behavior that resolves non-`BioConversation` dialogue strings.
- Implement one minimal semantic parser that upgrades at least one targeted probe from `container_fallback` to `semantic_container`.
- Preserve fallback behavior for unresolved containers, but make semantic precedence observable in report summaries and tests.
- Add focused fixtures or synthetic binary samples for the selected structure so parser behavior does not depend only on local game files.
- Acceptance gate:
  - at least one of the three narrative probes reports `strref_usage_source="semantic_container"`,
  - TLK hit counts remain unchanged,
  - fallback noise does not increase.

### Phase 12 - Evidence contract freeze and regression harness
- Introduce an explicit `evidence_schema_version` for evidence reports.
- Freeze required top-level fields and summary fields for production MVP workflows.
- Document evidence source tiers and expected precedence:
  - `bioconversation`,
  - `semantic_container`,
  - `container_fallback`.
- Add JSON contract tests for:
  - TLK-only discovery,
  - BioConversation usage,
  - semantic container usage,
  - raw fallback usage,
  - Go-index and Python-fallback parity.
- Create a reproducible regression harness for the three narrative probes with saved metrics and clear pass/fail thresholds.
- Acceptance gate:
  - report schema is stable and documented,
  - regression probes are reproducible from documented commands,
  - failures identify the broken stage (`tlk_scan`, `candidate_selection`, `candidate_parse`, or serialization).

### Phase 13 - Production MVP hardening and release candidate
- Finalize CLI command set and examples for production MVP usage:
  - extract conversations,
  - build/refresh Go candidate index,
  - generate evidence reports,
  - run targeted probes.
- Harden error handling and user-facing diagnostics for missing TLKs, missing DLC folders, compressed PCC limitations, stale indexes, and unsupported package profiles.
- Complete README/runbook updates with full commands, expected outputs, and troubleshooting notes.
- Run final QA across representative ME2 OT samples and any available LE2 samples.
- Produce a release-candidate note with:
  - supported games/profiles,
  - known limitations,
  - validation evidence,
  - LegendaryExplorer references used.
- Acceptance gate:
  - all Python and Go tests pass,
  - documented probes pass,
  - output contract tests pass,
  - MVP limitations are explicit rather than implicit.

## MVP acceptance criteria

- Given a valid `.pcc` with `BioConversation`, generate `output.json` without crashing.
- Include nodes, replies, speakers, `StrRef`, and resolved text (if available).
- If one conversation fails, report it and continue with the rest.
- Support at least ME2 OT on one real Citadel sample.

## Risks and mitigations

- OT vs LE serialization differences:
  - Mitigate with a per-version `game profile` layer.
- Incomplete/non-standard structures:
  - Mitigate with defensive parsing + warnings.
- DLC TLK overrides:
  - Mitigate with configurable load order.

## Immediate next step

1. Add Go ME2 OT LZO decompression using `github.com/anchore/go-lzo` and validate it against the existing Python `lzallright` behavior.
2. Re-run Phase 10 container-index probes and verify that `containers_by_file` coverage increases for compressed PCC candidates.
3. Start Phase 11 by using enriched offsets to identify the first inner serialized structure for semantic parsing.
