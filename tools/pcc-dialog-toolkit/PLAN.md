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

### Phase 9 - Persistent hybrid index and incremental scan
- Introduce a persistent StrRef candidate index generated by the Go scanner, with reusable metadata (`version`, `root_biogame`, `target_strrefs`, `files_scanned`, `candidates`, `hits_by_file`, `errors`).
- Add incremental refresh behavior keyed by file identity (mtime and size first, optional hash extension) to avoid full rescans on repeated workflows.
- Extend Python evidence workflows to consume persistent indexes directly and report candidate source + timing data for comparability.
- Define index lifecycle conventions:
  - build,
  - refresh,
  - invalidate,
  - consume.
- Add verification scenarios that compare:
  - full scan time,
  - incremental refresh time,
  - evidence output parity between full and incremental paths.

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

1. Implement persistent candidate index output + refresh command in the Go scanner.
2. Add Python CLI support to load a persistent index path and skip candidate regeneration when valid.
3. Run timing parity checks (full vs incremental) on the three narrative probes and record results.
