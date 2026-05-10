# PCC Toolkit v2 — Design Document

## 1. Project Goals

A unified CLI + GUI toolkit for inspecting, extracting, and analyzing Mass Effect 2 (Original Trilogy) `.pcc` dialogue packages. Built to serve both human modders (GUI) and AI agents (CLI with structured JSON output).

### Scope

- **Target**: Mass Effect 2 — Original Trilogy (ME2 OT)
- **Compression**: LZO only (ME2 OT compressed packages)
- **Legendary Edition**: Deferred. No LE1/LE2/LE3 support in v2. Will be added later.

### Guiding Principles

- **Go core = ALL domain logic**: parsing, AST building, graph layout, evidence assembly, serialization, validation. Nothing domain-related lives in Python.
- **CLI = thin dispatch layer**: parse args, call Go core via subprocess, format output. Zero domain logic.
- **GUI = pure renderer**: call Go core for data, render ImGui widgets. No parsing, no AST, no layout math.
- **JSON contract over stdout**: Go core speaks structured JSON; CLI and GUI consume it.
- **Gradual migration**: feature by feature, validate equivalence, compare outputs vs old toolkit, replace incrementally.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     pcc-toolkit v2                        │
│                                                           │
│  cli/                    gui/                             │
│  (Python, thin)          (Python, thin renderer)          │
│                                                           │
│  Typer CLI               Dear ImGui                      │
│  Arg parsing only        Widget rendering only            │
│  Formatting helpers      View state + interaction         │
│       │                       │                           │
│       └───────────┬───────────┘                           │
│                   │  subprocess, JSON stdin/stdout        │
│                   ▼                                       │
│  ┌────────────────────────────────────────────────┐      │
│  │              core/ (Go single binary)            │      │
│  │                                                  │      │
│  │  ALL domain logic (ME2 OT):                       │      │
│  │  ┌──────────────┐ ┌──────────────┐               │      │
│  │  │ PCC parsing   │ │ TLK handling  │               │      │
│  │  │ + LZO decomp  │ │ + DLC priority│               │      │
│  │  │ + properties  │ │ + resolution  │               │      │
│  │  │ + unreal props│ │               │               │      │
│  │  └──────────────┘ └──────────────┘               │      │
│  │  ┌──────────────┐ ┌──────────────┐               │      │
│  │  │ Dialogue AST  │ │ Evidence      │               │      │
│  │  │ + multi-mode  │ │ + scan        │               │      │
│  │  │ + validation  │ │ + profile     │               │      │
│  │  │ + graph layout│ │ + tiers       │               │      │
│  │  └──────────────┘ └──────────────┘               │      │
│  │  ┌──────────────┐ ┌──────────────┐               │      │
│  │  │ Serialization │ │ Batch         │               │      │
│  │  │ + JSON output │ │ + aggregate   │               │      │
│  │  │ + validation  │ │ + reports     │               │      │
│  │  └──────────────┘ └──────────────┘               │      │
│  └────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

### What lives WHERE

| Capability | Go core | Python CLI | Python GUI |
|---|---|---|---|
| PCC header/table parsing | **All** | — | — |
| LZO decompression | **All** | — | — |
| Property tag parsing | **All** | — | — |
| BioConversation AST building | **All** | — | — |
| Graph layout (Sugiyama) | **All** | — | — |
| TLK binary parsing | **All** | — | — |
| TLK DLC priority + Mount.dlc | **All** | — | — |
| StrRef resolution | **All** | — | — |
| Evidence scanning | **All** | — | — |
| Evidence report assembly | **All** | — | — |
| Narrative profiling | **All** | — | — |
| Validation | **All** | — | — |
| JSON serialization | **All** | — | — |
| Batch aggregation | **All** | — | — |
| CLI arg parsing | — | **All** | — |
| Terminal output formatting | — | **All** | — |
| Engine subprocess management | — | **All** | **All** |
| ImGui window/tab layout | — | — | **All** |
| Node/edge rendering (ImDrawList) | — | — | **All** |
| File open dialogs | — | — | **All** |
| UI state (selection, zoom, pan) | — | — | **All** |
| Error display | — | **All** | **All** |

---

## 3. Directory Structure

```
tools/pcc-toolkit-v2/
├── README.md
├── DESIGN.md                        # This document
├── pyproject.toml                   # Python project: CLI + GUI deps, scripts
│
├── core/                            # Go — ALL domain logic
│   ├── go.mod
│   ├── go.sum
│   ├── cmd/
│   │   └── pcc-core/
│   │       └── main.go              # Single binary, subcommand dispatch
│   └── internal/
│       ├── pcc/                     # PCC file parsing
│       │   ├── reader.go            # Header, name/import/export tables
│   │   ├── decompress.go        # LZO decompression (ME2 OT only)
│       │   ├── containers.go        # Offset-to-export mapping
│       │   ├── strings.go           # Unreal string reading, name resolution
│       │   ├── properties.go        # Property tag parser (ported from Python)
│       │   ├── unreal_props.go      # Semantic struct property parser (ported from Python)
│       │   ├── types.go             # pccHeader, pccExport, PropertyTag, etc.
│       │   └── reader_test.go
│       ├── dialogue/                # BioConversation parsing + AST
│       │   ├── ast.go               # EntryNode, ReplyNode, Speaker, Conversation types
│       │   ├── parser.go            # Multi-mode conversation parser (ported from Python)
│       │   ├── schema.go            # ME2 OT column schema
│       │   ├── validate.go          # Conversation validation
│       │   └── parser_test.go
│       ├── tlk/                     # TLK handling
│       │   ├── reader.go            # TLK binary parser + Huffman decode
│       │   ├── resolver.go          # DLC priority resolution (ported from Python)
│       │   ├── types.go             # TlkFile, TlkEntry
│       │   └── reader_test.go
│       ├── scan/                    # Parallel file scanning
│       │   ├── scanner.go           # Run, ParseStrrefs, findOffsets
│       │   ├── files.go             # CollectPccFiles
│       │   ├── index.go             # LoadIndex, SplitChangedFiles
│       │   ├── types.go             # Result, FileEntry, ContainerHit, Report
│       │   └── scanner_test.go
│       ├── evidence/                # Evidence/narrative search
│       │   ├── builder.go           # Tiered evidence assembly
│       │   ├── profile.go           # Narrative contextual profiles
│       │   └── builder_test.go
│       ├── graph/                   # Graph layout computation
│       │   ├── layout.go            # Sugiyama layout (ported from Python)
│       │   └── layout_test.go
│       ├── serialize/               # Output contract
│       │   ├── writer.go            # JSON payload builder + validator
│       │   └── writer_test.go
│       └── cli/                     # Shared utilities
│           └── flags.go             # Repeatable flag, validators
│
├── cli/                             # Python CLI (thin wrapper)
│   └── src/
│       └── pcc_toolkit/
│           ├── __init__.py          # __version__
│           ├── __main__.py          # → cli_main()
│           ├── cli_main.py          # Typer CLI, subcommand registration
│           ├── engine.py            # Go subprocess interface (shared with GUI)
│           └── format.py            # Terminal output formatting (tables, colors)
│
├── gui/                             # Python GUI (thin renderer)
│   └── src/
│       └── pcc_toolkit_gui/
│           ├── __init__.py
│           ├── app.py               # Main frame, menu, tab layout
│           ├── state.py             # UI state: selection, zoom, pan, paths
│           ├── engine.py            # Go subprocess interface (symlink or copy of CLI's)
│           └── views/
│               ├── __init__.py
│               ├── package.py       # Package viewer tab
│               ├── tlk.py           # TLK viewer tab
│               ├── dialogue.py      # Dialog explorer tab (graph + detail)
│               └── evidence.py      # Evidence search tab
│
├── tests/
│   ├── conftest.py                  # Shared fixtures: synthetic PCC/TLK builders
│   ├── test_core_contract.py        # Go core output contract tests
│   ├── test_cli.py                  # CLI dispatch tests
│   ├── test_gui.py                  # GUI module tests (no window)
│   ├── fixtures/
│   │   ├── pcc_builder.py           # Build synthetic PCC bytes
│   │   └── tlk_builder.py           # Build synthetic TLK bytes
│   └── golden/                      # Known-good output files for regression
│       ├── conversation/            # parse-conversations output
│       ├── tlk/                     # parse-tlk / resolve-tlk output
│       ├── evidence/                # scan-evidence output
│       └── graph/                   # layout-graph output
│
├── samples/                         # Real game files (gitignored)
│   └── README.md
├── output/                          # Generated output (gitignored)
│   └── .gitkeep
└── docs/
    ├── output-schema.md
    └── evidence-contract.md
```

---

## 3.1 Dependencies

### Go (`core/`)

| Package | Version | Purpose |
|---------|---------|---------|
| `github.com/anchore/go-lzo` | v0.1.0 | LZO1X decompression for ME2 OT compressed packages |
| `gonum.org/v1/gonum/graph` | latest | Graph representation and algorithms for Sugiyama layout |
| `encoding/json` | stdlib | JSON serialization (all subcommand output) |
| `flag` | stdlib | CLI flag parsing for subcommand dispatch |

No other external dependencies. The core binary is self-contained except for `go-lzo` and `gonum/graph`.

### Python CLI (`cli/`)

| Package | Version | Purpose |
|---------|---------|---------|
| `typer` | >=0.15 | CLI framework with subcommand groups, help text, shell completion |
| `rich` | >=13 | Terminal output formatting (tables, colors, progress bars) |

Stdlib only otherwise: `subprocess`, `json`, `pathlib`.

### Python GUI (`gui/`)

| Package | Version | Purpose |
|---------|---------|---------|
| `imgui-bundle` | >=1.90 | Dear ImGui bindings + HelloImGui for window/docking/layout |
| `python-igraph` | >=0.11 | **Dev only** — layout oracle for golden file generation and regression testing. Not a runtime dependency. |

Also depends on CLI packages (`typer`, `rich`). No other GUI runtime dependencies. Graph layout in production is done in Go core — the GUI only renders positions from `layout-graph` output.

### Dev-only dependencies (not in production)

| Package | Version | Purpose |
|---------|---------|---------|
| `python-igraph` | >=0.11 | Layout oracle: generate golden layouts, validate Go Sugiyama output, experiment with alternative algorithms. Used during development and regression testing, never at runtime. |
| `pytest` | >=9.0 | Test runner |

---

## 4. Go Core Specification (`core/`)

### 4.1 Binary Interface

```
pcc-core <subcommand> [flags]

Contract:
  - Input:  CLI flags + file paths (or stdin JSON for batch)
  - Output: JSON to stdout
  - Errors: JSON error object to stderr
  - Exit:   0 on success, non-zero on failure
  - Flag:   --pretty for indented output
```

### 4.2 Subcommands

#### `parse-pcc` — Parse a PCC file

```
pcc-core parse-pcc --file <path>
                   [--exports-only]
                   [--export-index <n>]
                   [--property-tags]
                   [--semantic-props]
```

**--exports-only**: Header + export tree (index, class_name, object_name, serial_offset, serial_size, game_profile)
**--export-index**: Full detail for one export including raw serial data (base64)
**--property-tags**: Include parsed PropertyTag list for each export
**--semantic-props**: Include full ParsedProperty name→value dicts for each export

Output includes `game_profile` (always `me2_ot` for v2 scope) and `compressed` flag.

#### `parse-conversations` — Parse BioConversations to AST

```
pcc-core parse-conversations --file <path>
                             [--conv-index <n>]
                             [--resolve-tlk <tlk_path>]
                             [--dlc-dir <path>]
                             [--mode resilient|strict]
```

Returns complete AST:
```json
{
  "file": "...",
  "game_profile": "me2_ot",
  "conversations": [
    {
      "id": "Conv_CitHub_Lia",
      "export_index": 5,
      "parse_mode": "struct_property_semantic",
      "entries": [
        { "id": 0, "speaker_id": 3, "speaker_tag": "LiaVael",
          "listener_tag": "Shepard", "line_strref": 12345,
          "line_text": "I can. Just point me where I'm needed.",
          "reply_links": [0, 1] }
      ],
      "replies": [
        { "id": 0, "line_strref": 12346,
          "line_text": "Good. Get to work.",
          "target_entry_id": 1,
          "condition_refs": ["cond_func:456"],
          "category": "Paragon" }
      ],
      "speakers": [
        { "id": 3, "tag": "LiaVael", "display_name": "Lia'Vael nar Tesleya" }
      ],
      "starts": [
        { "id": 0, "target_entry_id": 0, "label": "Start" }
      ],
      "warnings": []
    }
  ],
  "errors": []
}
```

Supports all 4 parse modes: `struct_property_semantic`, `row_payload`, `row_payload_struct_matrix`, `row_payload_struct_head`. Falls back gracefully.

TLK resolution is built-in: if `--resolve-tlk` is provided, `line_text` is populated from the TLK (including DLC overrides via `--dlc-dir`).

#### `layout-graph` — Compute graph positions

```
pcc-core layout-graph --file <path>
                      [--conv-index <n>]
                      [--algorithm sugiyama|tree|force]
                      [--node-width <px>] [--node-height <px>]
                      [--x-spacing <px>] [--y-spacing <px>]
```

Takes a PCC file (internally calls parse-conversations), then computes 2D positions for every node. Returns:
```json
{
  "conversation_id": "Conv_CitHub_Lia",
  "node_count": 24,
  "positions": {
    "start:0": [100.0, 50.0],
    "entry:0": [100.0, 200.0],
    "reply:0": [400.0, 200.0],
    ...
  },
  "edges": [
    { "from": "start:0", "to": "entry:0" },
    { "from": "entry:0", "to": "reply:0" },
    ...
  ]
}
```

GUI calls this when a conversation is selected. No layout logic in Python.

Uses a pure Go graph layout implementation to avoid depending on igraph at runtime. The layout engine is implemented iteratively:

**v1 — Barycenter heuristic:**
- Simple layer assignment (BFS from starts and replies)
- Barycenter crossing minimization
- Basic horizontal spacing
- Straight-line edges

**v2 — Full Sugiyama:**
- Dummy nodes for long edges
- Proper edge routing with bend points
- Cycle removal heuristic
- Weighted node ordering

`python-igraph` is kept as a **development oracle**: during implementation, Go output is compared against igraph's `layout_sugiyama()` to validate layering quality, crossing minimization, and coordinate placement. igraph generates golden layouts committed to `tests/golden/graph/`. It is not a runtime dependency.

#### `parse-tlk` — Parse a TLK file

```
pcc-core parse-tlk --file <path>
                   [--search <query>]
                   [--strref <id>]
                   [--dump-all]
```

Returns all entries, or filtered by search/strref. Handles Huffman tree, bit decode, male/female string tables.

#### `resolve-tlk` — Resolve with DLC priority

```
pcc-core resolve-tlk --base <path>
                     --dlc-dir <path>
                     --strref <id> [--strref <id> ...]
```

Scans DLC directories, reads Mount.dlc for MountPriority, builds priority-ordered resolver, resolves each StrRef. Returns first-match text per StrRef.

#### `scan-evidence` — Full evidence report

```
pcc-core scan-evidence --query <text>
                       --tlk <path>
                       [--dlc-dir <path>]
                       [--biogame-root <path>]
                       [--auto-index]
                       [--candidate-index <path>]
                       [--workers <n>]
```

The big one. Pipeline:
1. Search TLK for query → candidate StrRefs
2. Parallel scan all .pcc files for those StrRefs
3. Parse candidate PCCs, extract BioConversations
4. Resolve StrRefs in AST nodes
5. Build tiered evidence (BioConversation > semantic_container > container_fallback)
6. Apply narrative profile weighting
7. Return complete evidence report JSON

#### `validate` — Validate conversations

```
pcc-core validate --file <path> [--strict]
```

Returns per-conversation validation report: valid/invalid/needs_schema_review, specific issues per conversation.

#### `serialize` — Output contract

```
pcc-core serialize --file <path>
                   [--output <path>]
                   [--game <profile>]
                   [--resolve-tlk <path>]
                   [--dlc-dir <path>]
                   [--pretty]
```

Full pipeline: parse PCC → parse conversations → resolve TLK → validate → serialize to output JSON. This is the `pcc-toolkit package extract` backend.

#### `batch-validate` — Batch validation

```
pcc-core batch-validate --dir <path>
                        [--glob <pattern>]
                        [--strict]
                        [--output <path>]
```

Aggregates validation across multiple PCC files. For scripting / AI agent use.

#### `version` — Version and capabilities

```
pcc-core version
```

```json
{
  "version": "0.2.0",
  "target": "me2_ot",
  "capabilities": [
    "pcc_parse_v1",
    "pcc_property_tags_v1",
    "pcc_semantic_props_v1",
    "conversation_ast_v1",
    "graph_layout_v1",
    "tlk_parse_v1",
    "tlk_dlc_resolve_v1",
    "evidence_scan_v1",
    "validate_v1",
    "serialize_v1",
    "batch_validate_v1"
  ]
}
```

### 4.3 Complete AST Specification

All fields below must be extracted by the Go core's `parse-conversations` subcommand. This spec incorporates all known ME2 OT BioConversation data fields, including those identified as gaps (B-GAP-1 through B-GAP-15) in the original GUI development branch.

#### EntryNode
```json
{
  "id": 0,
  "speaker_id": 3,
  "speaker_tag": "LiaVael",
  "listener_tag": "Shepard",
  "line_strref": 12345,
  "line_text": "I can. Just point me where I'm needed.",
  "reply_links": [0, 1]
}
```
| Field | Type | Required | Source |
|-------|------|----------|--------|
| `id` | int | Always | EntryList[n].nIndex or array position |
| `speaker_id` | int | When available | EntryList[n].nSpeakerIndex |
| `speaker_tag` | string | When available | Resolved from SpeakerList via speaker_id |
| `listener_tag` | string | When available | Name table index from EntryList row, or nListenerIndex in semantic mode |
| `line_strref` | int | When available | EntryList[n].srText or row strref column |
| `line_text` | string | When TLK resolved | Resolved via TLK + DLC priority |
| `reply_links` | int[] | Always | ReplyList entries whose nEntryIndex targets this entry |

#### ReplyNode
```json
{
  "id": 0,
  "line_strref": 12346,
  "line_text": "Good. Get to work.",
  "target_entry_id": 1,
  "conditions": [
    { "func_ref": 456, "param": 0, "func_name": "CheckMissionComplete" }
  ],
  "category": "Paragon"
}
```
| Field | Type | Required | Source |
|-------|------|----------|--------|
| `id` | int | Always | ReplyList[n].nIndex or array position |
| `line_strref` | int | When available | ReplyList[n].srText |
| `line_text` | string | When TLK resolved | Resolved via TLK + DLC priority |
| `target_entry_id` | int | When available | ReplyList[n].nEntryIndex (B-GAP-4) |
| `conditions` | Condition[] | When available | ReplyList[n].nConditionalFunc + nConditionalParam, resolved via name table (B-GAP-8) |
| `category` | string | When available | ReplyListNew[i].Category: Paragon, Renegade, Agree, Disagree, Friendly, Hostile, Interrupt (B-GAP-1) |

#### Condition
```json
{ "func_ref": 456, "param": 0, "func_name": "CheckMissionComplete" }
```
| Field | Type | Required | Source |
|-------|------|----------|--------|
| `func_ref` | int | Always | nConditionalFunc from reply struct |
| `param` | int | Always | nConditionalParam from reply struct |
| `func_name` | string | When resolvable | Name table entry at func_ref index |

#### Speaker
```json
{ "id": 3, "tag": "LiaVael", "display_name": "Lia'Vael nar Tesleya" }
```
| Field | Type | Required | Source |
|-------|------|----------|--------|
| `id` | int | Always | SpeakerList[n].nIndex or array position |
| `tag` | string | When available | SpeakerList[n].sSpeakerTag (B-GAP-4) |
| `display_name` | string | When available | SpeakerList[n].nDisplayNameStrRef, resolved via TLK (B-GAP-9) |

#### StartNode
```json
{ "id": 0, "target_entry_id": 0, "label": "Start" }
```
| Field | Type | Required | Source |
|-------|------|----------|--------|
| `id` | int | Always | m_StartingList[n] array position |
| `target_entry_id` | int | When available | StartingList[n].nEntryIndex (B-GAP-4) |
| `label` | string | Optional | Default "Start", customizable if data available |

#### StageDirection (future)
| Field | Type | Source |
|-------|------|--------|
| `id` | int | Array position |
| `text` | string | Embedded text or StrRef |

Note: StageDirection extraction requires data exploration to determine the PCC property mechanism. Deferred until confirmed in ME2 OT files (B-GAP-7).

#### Conversation (top-level)
| Field | Type | Required |
|-------|------|----------|
| `id` | string | Export object name |
| `export_index` | int | Export table index |
| `game_profile` | string | Always "me2_ot" |
| `parse_mode` | string | struct_property_semantic, row_payload, row_payload_struct_matrix, row_payload_struct_head, count_or_value_fallback |
| `entries` | EntryNode[] | Parsed |
| `replies` | ReplyNode[] | Parsed |
| `speakers` | Speaker[] | Parsed |
| `starts` | StartNode[] | Parsed |
| `stage_directions` | StageDirection[] | Future (B-GAP-7) |
| `warnings` | string[] | Parse warnings |

### 4.4 Go Internal Package Map

```
core/internal/
├── pcc/
│   ├── reader.go          ← from old internal/scan/pcc.go (header, tables)
│   ├── decompress.go      ← from old internal/scan/pcc.go (LZO)
│   ├── containers.go      ← from old internal/scan/pcc.go (offset mapping)
│   ├── strings.go         ← from old internal/scan/pcc.go (unreal strings)
│   ├── properties.go      ← PORT from Python pcc/properties.py
│   ├── unreal_props.go    ← PORT from Python pcc/unreal_props.py
│   └── types.go           ← from old internal/scan/types.go + new types
├── dialogue/
│   ├── ast.go             ← PORT from Python model/ast.py
│   ├── parser.go          ← PORT from Python dialogue/conversation_parser.py
│   ├── schema.go          ← PORT from Python dialogue/schema.py
│   └── validate.go        ← PORT from Python validation logic
├── tlk/
│   ├── reader.go          ← NEW Go implementation (or port from Python)
│   ├── resolver.go        ← PORT from Python tlk/resolver.py
│   └── types.go
├── scan/
│   ├── scanner.go         ← from old internal/scan/scanner.go
│   ├── files.go           ← from old internal/scan/files.go
│   ├── index.go           ← from old internal/scan/index.go
│   └── types.go           ← from old internal/scan/types.go
├── evidence/
│   ├── builder.go         ← PORT from Python cli.py evidence logic
│   └── profile.go         ← PORT from Python narrative profiles
├── graph/
│   └── layout.go          ← PORT from Python gui/graph/layout.py
├── serialize/
│   └── writer.go          ← PORT from Python serialize/json_writer.py
└── cli/
    └── flags.go           ← from old cmd/pcc-scan/main.go multiFlag
```

### 4.5 Data Flow: GUI Opens a File

```
User clicks "Load" in GUI
    │
    ▼
gui/views/package.py calls engine.parse_pcc(file, exports_only=True)
    │
    ▼
Subprocess: pcc-core parse-pcc --file "BioD_CitHub.pcc" --exports-only
    │
    ▼
Go core:
  1. Reads file bytes
  2. Decompresses if needed (LZO)
  3. Parses header, names, imports, exports
  4. Resolves class names, object names
  5. Infers game profile
  6. Serializes to JSON
  7. Writes JSON to stdout
    │
    ▼
Python engine.py reads stdout, returns dict
    │
    ▼
gui/state.py stores: pcc_data = { exports: [...], game_profile: "me2_ot", ... }
    │
    ▼
gui/views/package.py renders tree view from pcc_data["exports"]
```

### 4.6 Data Flow: GUI Selects a Conversation

```
User clicks a conversation in GUI
    │
    ▼
gui/views/dialogue.py calls:
  1. engine.layout_graph(file, conv_index=5)  → node positions
  2. engine.parse_conversations(file, conv_index=5, resolve_tlk=..., dlc_dir=...) → AST with text
    │
    ▼
Go core layout-graph:
  1. Parses PCC
  2. Parses conversation #5 to AST
  3. Builds directed graph
  4. Runs Sugiyama layout
  5. Returns positions + edges
    │
    ▼
Go core parse-conversations:
  1. Parses conversation #5 to AST (may reuse cached parse)
  2. Resolves all StrRefs against TLK + DLC
  3. Returns AST with populated line_text
    │
    ▼
Python GUI receives both results
    │
    ▼
gui/views/dialogue.py:
  1. Renders nodes at positions (ImDrawList circles/rects)
  2. Renders edges as bezier curves
  3. Renders text labels on nodes
  4. Handles click hit-testing (in Python, since it's viewport math)
```

Note: hit-testing (which node did the user click?) is viewport math → stays in GUI. But node positions come from Go.

---

## 5. Python CLI Specification (`cli/`)

### 5.1 Purpose

- Parse user args (Typer)
- Validate paths exist
- Call Go core subprocess
- Format output for terminal (tables, colors, JSON dump)
- Handle errors gracefully
- **Zero domain logic**

### 5.2 Subcommand Tree

```
pcc-toolkit
├── package
│   ├── list <file> [--class CLASS] [--json]
│   ├── inspect <file> <index> [--json]
│   ├── validate <file> [--strict] [--json]
│   └── extract <file> [--output PATH] [--game PROFILE]
│                      [--tlk PATH] [--dlc-dir PATH] [--pretty]
│
├── tlk
│   ├── info <file> [--json]
│   ├── search <query> [--tlk PATH] [--dlc-dir PATH] [--json]
│   ├── resolve <strref> [--tlk PATH] [--dlc-dir PATH] [--json]
│   └── dump <file> [--output PATH]
│
├── dialogue
│   ├── list <file> [--json]
│   ├── export <file> [--output PATH] [--tlk PATH] [--dlc-dir PATH] [--pretty]
│   ├── graph <file> [--conv INDEX] [--format json|dot]
│   └── inspect <file> <conv> <node> [--json]
│
├── evidence
│   ├── scan <query> [--tlk PATH] [--dlc-dir PATH] [--biogame-root PATH]
│   │                [--auto-index] [--output PATH] [--json]
│   ├── profile <query> [--json]
│   ├── trace <strref> [--tlk PATH] [--dlc-dir PATH] [--biogame-root PATH]
│   └── query <report> <filter> [--json]
│
├── batch
│   ├── validate <dir> [--glob PATTERN] [--output PATH] [--strict]
│   ├── extract <dir> [--glob PATTERN] [--output-dir PATH]
│   │                [--tlk PATH] [--dlc-dir PATH]
│   └── probe <config>  # Regression probes from YAML config
│
├── gui                     # Launch interactive GUI
│
├── dev
│   ├── build-core          # go build -o pcc-core core/cmd/pcc-core
│   └── test-core           # go test ./core/...
│
└── --version / --help
```

### 5.3 Shared Engine Interface

Both CLI and GUI use the same `engine.py`. The GUI symlinks or copies it.

```python
# Shared between cli/ and gui/
# src/pcc_toolkit/engine.py  and  gui/src/pcc_toolkit_gui/engine.py

import subprocess, json
from pathlib import Path
from typing import Any

CORE_BINARY = "pcc-core"  # or pcc-core.exe on Windows

class EngineError(Exception): ...

def _run(subcommand: str, **kwargs) -> dict[str, Any]:
    args = [CORE_BINARY, subcommand]
    for key, value in kwargs.items():
        flag = f"--{key.replace('_', '-')}"
        if isinstance(value, bool):
            if value: args.append(flag)
        elif isinstance(value, list):
            for v in value: args.extend([flag, str(v)])
        elif value is not None:
            args.extend([flag, str(value)])
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise EngineError(proc.stderr.strip())
    return json.loads(proc.stdout)

# One function per Go subcommand:
def parse_pcc(file: Path, *, exports_only=False, export_index=None,
              property_tags=False, semantic_props=False) -> dict:
    return _run("parse-pcc", file=str(file), exports_only=exports_only,
                export_index=export_index, property_tags=property_tags,
                semantic_props=semantic_props)

def parse_conversations(file: Path, *, conv_index=None, resolve_tlk=None,
                        dlc_dir=None, mode="resilient") -> dict:
    return _run("parse-conversations", file=str(file), conv_index=conv_index,
                resolve_tlk=resolve_tlk, dlc_dir=dlc_dir, mode=mode)

def layout_graph(file: Path, *, conv_index=None, algorithm="sugiyama",
                 node_width=240, node_height=64,
                 x_spacing=80, y_spacing=120) -> dict:
    return _run("layout-graph", file=str(file), conv_index=conv_index,
                algorithm=algorithm, node_width=node_width,
                node_height=node_height, x_spacing=x_spacing,
                y_spacing=y_spacing)

def parse_tlk(file: Path, *, search=None, strref=None, dump_all=False) -> dict:
    return _run("parse-tlk", file=str(file), search=search,
                strref=strref, dump_all=dump_all)

def resolve_tlk(base: Path, dlc_dir: Path, strrefs: list[int]) -> dict:
    return _run("resolve-tlk", base=str(base), dlc_dir=str(dlc_dir),
                strref=strrefs)

def scan_evidence(query: str, *, tlk: Path, dlc_dir=None,
                  biogame_root=None, auto_index=False,
                  candidate_index=None, workers=0) -> dict:
    return _run("scan-evidence", query=query, tlk=str(tlk),
                dlc_dir=dlc_dir, biogame_root=biogame_root,
                auto_index=auto_index, candidate_index=candidate_index,
                workers=workers)

def validate(file: Path, *, strict=False) -> dict:
    return _run("validate", file=str(file), strict=strict)

def serialize(file: Path, *, game=None, resolve_tlk=None,
              dlc_dir=None, pretty=False) -> dict:
    return _run("serialize", file=str(file), game=game,
                resolve_tlk=resolve_tlk, dlc_dir=dlc_dir, pretty=pretty)

def batch_validate(dir: Path, *, glob_pattern=None,
                   strict=False) -> dict:
    return _run("batch-validate", dir=str(dir), glob=glob_pattern,
                strict=strict)

def version() -> dict:
    return _run("version")
```

---

## 6. Python GUI Specification (`gui/`)

### 6.0 Reference: LegendaryExplorer Dialog Editor

LegendaryExplorer (LEX) is the reference tool for ME trilogy modding. Its Dialog Editor uses:
- **Piccolo.NET** for the zoomable canvas (`PCanvas` with backLayer, edgeLayer, nodeLayer)
- **DStart** (green, UID ≥ 2000), **DiagNodeEntry** (gold, UID < 1000), **DiagNodeReply** (blue-gray, UID 1000–1999)
- **DiagEdEdge** bezier curves with category-driven colors
- **Full read/write** editing of underlying StructProperty data

Our v2 GUI matches LEX in **visual presentation** (node colors, edge categories, bezier curves, dual-line labels) but is **read-only** by design. Write support is deferred.

### 6.1 Purpose

- Render ImGui windows, tabs, tables, graphs
- Manage UI-only state (selection, zoom, pan, filter text, tab index)
- Call Go core subprocesses for ALL data
- Display loading/error states
- File open dialogs
- **Zero domain logic**

### 6.2 UI State (`state.py`)

```python
@dataclass
class AppState:
    # File paths (set by user via file dialogs)
    pcc_path: str | None = None
    tlk_path: str | None = None
    dlc_dir: str | None = None

    # Data caches (results from Go core calls)
    pcc_exports: dict | None = None       # from parse_pcc(exports_only=True)
    tlk_entries: dict | None = None       # from parse_tlk(dump_all=True)
    conversations: dict | None = None     # from parse_conversations(resolve_tlk=...)
    graph_layout: dict | None = None      # from layout_graph(conv_index=...)

    # UI selection state
    selected_export_index: int | None = None
    selected_conversation_index: int | None = None
    selected_node_key: str | None = None   # "entry:5", "reply:3", "start:0"

    # Viewport state
    graph_view_offset: tuple[float, float] = (0.0, 0.0)
    graph_view_zoom: float = 1.0

    # Transient UI state
    status_message: str = "Ready"
    is_loading: bool = False
    error_message: str | None = None
    conv_filter: str = ""
    tlk_search: str = ""
    evidence_query: str = ""
    evidence_results: dict | None = None

    active_tab: int = 2  # Default to Dialog Explorer
    show_about: bool = False
```

Note: **No domain objects in state**. No `PccPackage`, no `TlkResolver`, no `Conversation` AST objects. Just the JSON dicts from Go core. The GUI renders from dicts.

### 6.3 Views

Each view file is a single function `render_<view>(state: AppState)` that renders ImGui widgets using data from `state` dicts. No parsing, no computation beyond viewport math.

#### `views/package.py`
- Left panel: tree view from `state.pcc_exports["exports"]`, grouped by `class_name`
- Right panel: detail from `state.pcc_exports` for selected export
- "Load PCC" button → calls `engine.parse_pcc()`, stores in `state.pcc_exports`
- "Validate Stubs" button → calls `engine.validate()`, shows results

#### `views/tlk.py`
- Top bar: TLK path, DLC dir, search field
- Table from `state.tlk_entries["entries"]` — StringID, Text columns
- Search calls `engine.parse_tlk(search=...)`, updates table
- Stats footer: total entries, DLC overrides count

#### `views/dialogue.py`
- Left: file loader (same as package), conversation list, detail panel
- Right: graph view — renders from `state.graph_layout["positions"]` and `state.graph_layout["edges"]`
- Selecting a conversation → calls `engine.layout_graph()` + `engine.parse_conversations()`
- Node rendering: blue entries, orange replies, green starts
- Bezier edges with arrowheads
- Click hit-testing: viewport math only (screen coords → world coords → node key)
- Detail panel: shows selected node data from `state.conversations` dict

#### `views/evidence.py` (NEW)
- Query bar + search button
- Results in expandable tree: BioConversation tier → semantic_container tier → container_fallback tier
- Each leaf shows file path + conversation name + matched text
- "Export Report" button saves full JSON
- Calls `engine.scan_evidence(query=..., tlk=..., dlc_dir=..., biogame_root=...)`

### 6.4 Graph Rendering Details

Reference: LegendaryExplorer Dialog Editor node/edge conventions.

#### Node Types and Colors

| Node Type | Shape | Color | Notes |
|-----------|-------|-------|-------|
| Start | Rounded rect | Green (#4CAF50) | Conversation entry point |
| Entry | Rectangle | Blue (#2196F3) | NPC dialogue line |
| Reply | Rectangle | Orange (#FF9800) | Player response choice |

Text layout per node (dual-line):
- Line 1: Speaker tag (entries) or "Reply" label (replies), bold
- Line 2: Line text, truncated to ~60 chars, normal weight

#### Edge Colors by Reply Category

Per LEX convention, reply edges are colored by `EReplyCategory`:

| Category | Edge Color | Hex |
|----------|-----------|-----|
| Paragon / Paragon Interrupt | Blue | #448AFF |
| Renegade / Renegade Interrupt | Red | #F44336 |
| Agree | Dodger blue | #1E90FF |
| Disagree | Tomato | #FF6347 |
| Friendly | Dark blue | #1565C0 |
| Hostile | Dark red | #C62828 |
| Default (no category) | Gray | #9E9E9E |

All edges are cubic bezier curves with arrowheads at the target end. Control points are computed with horizontal offset for readability (no straight lines between overlapping nodes).

#### Graph Layout Algorithms

The Go core `layout-graph` subcommand supports:

| Algorithm | Flag | Description |
|-----------|------|-------------|
| Sugiyama | `--algorithm sugiyama` (default) | Layered digraph layout. Best for conversation trees. |
| Reingold-Tilford | `--algorithm tree` | Waterfall-style tree layout. Good for linear conversations. |
| Kamada-Kawai | `--algorithm force` | Force-directed layout. Fallback for cyclic graphs. |

The GUI provides a layout selector dropdown and a "Re-layout" button that re-calls `pcc-core layout-graph`.

#### Viewport Interaction (GUI-only)

- **Zoom**: Mouse wheel, centered on cursor position. Range: 0.1x – 5.0x.
- **Pan**: Right-click drag. Accumulated in `graph_view_offset`.
- **Click-to-select**: Hit-test against node bounding boxes, transformed through zoom + offset.
- **Grid background**: Subtle dot grid rendered behind the graph.
- **Legend**: Fixed overlay box showing node colors + edge category colors.

Note: All hit-testing is viewport math (screen → world transform) and stays in Python GUI. Node positions, edges, and categories come from Go core.

---

## 7. Migration Strategy (Gradual, Feature by Feature)

### Principle
- Keep old toolkit working at all times
- Build v2 feature → validate output matches old toolkit → replace → move to next
- Each feature is independently testable
- **All validation against ME2 OT files only** (no LE/ME3 test data)
- **Golden files protect against regressions during ports**: every capability has a known-good output file in `tests/golden/` that serves as the structural contract

### Golden Test Strategy

Golden files are **known-good JSON outputs** produced by the old toolkit (or the first correct v2 implementation) against a fixed set of ME2 OT input files. They live in `tests/golden/` and are committed to the repository.

```
tests/golden/
├── conversation/
│   ├── BioD_CitHub_300Dialogue_LOC_INT.json    # parse-conversations output
│   └── BioD_CitHub_LOC_INT.json
├── tlk/
│   ├── BIOGame_INT_strref_12345.json           # parse-tlk --strref output
│   └── BIOGame_INT_dump_first_100.json         # parse-tlk --dump-all (first 100)
├── evidence/
│   ├── rally_the_crowd.json                    # scan-evidence "rally the crowd"
│   ├── tali_intimacy.json                      # scan-evidence "tali intimacy"
│   └── miss_vas_normandy.json                  # scan-evidence "Miss vas Normandy"
└── graph/
    ├── BioD_CitHub_300Dialogue_sugiyama.json   # layout-graph --algorithm sugiyama
    └── BioD_CitHub_300Dialogue_tree.json       # layout-graph --algorithm tree
```

**Workflow during porting:**

1. Run old toolkit against known input → save output as golden file
2. Port feature to Go core
3. Run Go core against same input
4. Compare output to golden file (structural equivalence, not exact string match)
5. If match: port is correct. If mismatch: investigate and fix.
6. Golden files are never edited manually — only regenerated when the contract intentionally changes.

**Golden file rules:**
- Committed to repo (they are small JSON, not binaries)
- One golden file per capability × input combination
- Input files are ME2 OT PCC/TLK files stored in `samples/` (gitignored)
- Golden files include `schema_version` to detect contract drift

### Phase 1: Core Skeleton
1. Create directory structure (`core/`, `cli/`, `gui/`)
2. Initialize `core/go.mod`, `pyproject.toml`
3. Build `core/cmd/pcc-core/main.go` with `version` subcommand
4. Build `cli/src/pcc_toolkit/engine.py` (shared interface)
5. Build `cli/src/pcc_toolkit/cli_main.py` with `--version` and `--help`
6. Verify: `python -m pcc_toolkit --version` → calls Go → prints version

### Phase 2: PCC Parsing (Go)
1. Port `internal/scan/pcc.go` → `core/internal/pcc/` (reader, decompress, containers, strings, types)
2. Build `parse-pcc` subcommand in Go
3. Validate: compare `pcc-core parse-pcc --file BioD_CitHub.pcc --exports-only` output against old `pcc_dialog_extract --list-bioconversations`
4. Wire to CLI: `pcc-toolkit package list <file>` working

### Phase 3: TLK Parsing (Go)
1. Port `src/tlk/reader.py` → `core/internal/tlk/reader.go` (Go implementation of Huffman decoder)
2. Port `src/tlk/resolver.py` → `core/internal/tlk/resolver.go` (DLC priority)
3. Build `parse-tlk` and `resolve-tlk` subcommands
4. Validate: compare output against old Python TLK reader/resolver
5. Wire to CLI: `pcc-toolkit tlk search|resolve|info` working

### Phase 4: Conversation Parsing (Go)
1. Port `src/pcc/properties.py` → `core/internal/pcc/properties.go`
2. Port `src/pcc/unreal_props.py` → `core/internal/pcc/unreal_props.go`
3. Port `src/model/ast.py` → `core/internal/dialogue/ast.go`
4. Port `src/dialogue/conversation_parser.py` → `core/internal/dialogue/parser.go`
5. Port `src/dialogue/schema.py` → `core/internal/dialogue/schema.go`
6. Build `parse-conversations` subcommand
7. Validate: compare AST output against old toolkit for known PCC files
8. Wire to CLI: `pcc-toolkit dialogue list|export|inspect` working

### Phase 5: Graph Layout (Go)
1. Port `src/gui/graph/layout.py` → `core/internal/graph/layout.go`
2. Use `gonum/graph` or implement Sugiyama directly
3. Build `layout-graph` subcommand
4. Validate: positions match old Python layout for known conversations

### Phase 6: Evidence (Go)
1. Port evidence builder from `src/cli.py` → `core/internal/evidence/builder.go`
2. Port narrative profiles → `core/internal/evidence/profile.go`
3. Port parallel scanner (already in Go, just wire to evidence pipeline)
4. Build `scan-evidence` subcommand
5. Validate: run same probes as `scripts/run_probe_regression.py`, compare reports

### Phase 7: Serialization + Validation (Go)
1. Port `src/serialize/json_writer.py` → `core/internal/serialize/writer.go`
2. Port validation logic → `core/internal/dialogue/validate.go`
3. Build `serialize` and `validate` subcommands
4. Wire to CLI: `pcc-toolkit package extract|validate` working

### Phase 8: CLI Polish
1. Batch commands (`batch validate|extract|probe`)
2. Pretty terminal output (tables, colors via Rich)
3. Shell completion
4. Error messages and user guidance

### Phase 9: GUI
1. Build `gui/src/pcc_toolkit_gui/` with empty tabs
2. Implement Package tab (uses `parse-pcc`)
3. Implement TLK tab (uses `parse-tlk`)
4. Implement Dialog tab (uses `layout-graph` + `parse-conversations`)
5. Implement Evidence tab (uses `scan-evidence`)
6. Test: load real files, verify all views render correctly

### Phase 10: QA & Cutover
1. Run full old test suite against v2 (adapt paths)
2. Run regression probes against v2
3. Compare preprod-all batch output
4. Add deprecation notice to old toolkit README
5. Archive old toolkit

---

## 8. Known Bugs from Old Toolkit — Fixed in v2

| Bug | Old Location | Fix in v2 |
|-----|-------------|-----------|
| `from cli import main` broken import | `src/__main__.py` | `from .cli_main import main` |
| `graph_layout: dict[int, ...]` wrong type | `gui/state.py` | Corrected to `dict[str, tuple[float, float]]` |
| `_read_i32` marked private, widely imported | `pcc/reader.py` | Public function in Go core |
| 3 copies of `_resolve_name` | `pcc/` modules | Single implementation in Go core |
| 2 copies of `PROPERTY_TYPE_NAMES` | `pcc/` modules | Single definition in Go core |
| 5 duplicate TLK resolution blocks | `cli.py` | Single `resolve-tlk` Go subcommand |
| `infer_game_profile` missing me1/le1 | `pcc/models.py` | Not in v2 scope (ME2 OT only, profile is explicit) |
| `me3_ot`/`le3` schemas lack columns | `dialogue/schema.py` | Not in v2 scope (ME2 OT only) |
| Hardcoded Lia'Vael keywords | `cli.py` | Configurable profiles in Go core |
| `layout_conversation` unused params | `gui/graph/layout.py` | Properly used in Go core |
| `PccPackage` 21 methods (god class) | `pcc/models.py` | Functions in Go, not methods on data |

---

## 9. Key Design Decisions

### 9.1 Why all domain logic in Go?

- **Single source of truth**: One implementation of parsing, no Python/Go duplication
- **Performance**: Binary parsing, graph layout, batch processing all faster in Go
- **Distribution**: Single Go binary + thin Python wrapper = easy to deploy
- **Testability**: Go tests are fast, deterministic, no Python environment issues
- **GUI stays thin**: Can swap GUI framework (ImGui → Qt → web) without touching domain logic

### 9.2 Why JSON over stdout?

- No serialization format to design or maintain
- Debuggable: pipe Go output to file, inspect visually
- Works across any language (future: Rust GUI? Web frontend?)
- No shared memory, FFI, or linking complexity

### 9.3 Why separate `cli/` and `gui/` as top-level directories?

- Clear separation of concerns visible at file system level
- Different dependency sets (GUI needs `imgui-bundle`, CLI doesn't)
- Can install CLI without GUI deps: `pip install .[cli]`
- Each has its own `engine.py` (or symlink) — decoupled

### 9.4 What happens if Go core is not available?

- `pcc-toolkit dev build-core` compiles it
- CLI/GUI print clear error: "pcc-core not found. Run: pcc-toolkit dev build-core"
- Pre-built binaries provided in GitHub releases
- No Python fallback for domain logic (by design — no duplication)

### 9.6 ME2 OT only — Legendary Edition deferred

- All binary parsing assumes ME2 OT format (Unreal version 512, licensee version 130)
- LZO decompression only (no Oodle for LE)
- Schema columns calibrated for ME2 OT BioConversation layout
- `--game` flag exists in CLI but only `me2` is validated
- LE support will be a separate milestone after v2 is stable

### 9.7 Why Go-native graph layout instead of igraph at runtime?

- `igraph` is a C library with Python bindings — architecturally wrong when the AST and graph model live in Go. Keeping layout in Python would create model duplication, intermediate format drift, and cross-language debugging friction.
- Conversation graph layout is **domain logic**: it understands starts, entries, replies, categories, and branch semantics. It belongs in the core.
- `python-igraph` remains as a **development oracle**: used during implementation to validate Go output against igraph's Sugiyama, generate golden layouts, and experiment with alternative algorithms. Not a runtime dependency.
- Implementing Sugiyama in Go is iterative: v1 = barycenter heuristic, v2 = full Sugiyama with dummy nodes. Each step validated against igraph golden output.

---

## 10. Success Criteria

A user (human or AI agent) working with **Mass Effect 2 Original Trilogy** can:

1. Install with `pip install .[cli]` or `pip install .[gui]`
2. Build core with `pcc-toolkit dev build-core`
3. Run `pcc-toolkit package list BioD_CitHub.pcc` → see export tree
4. Run `pcc-toolkit dialogue export BioD_CitHub.pcc --tlk BIOGame_INT.tlk` → get JSON with resolved text
5. Run `pcc-toolkit evidence scan "quarian pilgrimage" --tlk ... --dlc-dir ... --biogame-root ...` → get evidence report
6. Launch GUI, load a PCC, explore ME2 conversation graph interactively
7. Run `pcc-toolkit batch extract "C:\ME2\BioGame\CookedPC" --glob "BioD_*LOC_INT.pcc" --tlk ...` → get JSON for every file
8. Get identical output (within tolerance) to old toolkit for same ME2 OT inputs
