# GUI PLAN — PCC Dialog Viewer

## 1. LegendaryExplorer Dialogue Editor: Internal Architecture

Reference: `LegendaryExplorer/LegendaryExplorer/Tools/Dialogue Editor/`

### 1.1 Graph engine
Uses **Piccolo.NET** (2D zoomable canvas). `ConvGraphEditor` extends `PCanvas`:

| Layer | Purpose |
|---|---|
| `backLayer` | Background elements |
| `edgeLayer` | Bezier curves connecting nodes |
| `nodeLayer` | Draggable, selectable conversation nodes |

`ZoomController` handles mouse wheel (±0.1%) and Ctrl+/- (0.8x / 1.2x).

### 1.2 Node types
All extend `DObj → DBox`, each with a `NodeUID` band:

| Class | UID range | Color | Represents |
|---|---|---|---|
| `DStart` | ≥ 2000 | Green | Conversation start points |
| `DiagNodeEntry` | < 1000 | Gold | NPC dialogue line |
| `DiagNodeReply` | 1000–1999 | Blue-gray | Player response choice |

### 1.3 Edge system
`DiagEdEdge` extends `PPath` (bezier curves). Connections resolved from raw property arrays:

- **Entry → Reply**: `EntryList[n].ReplyListNew[i].nIndex`
- **Reply → Entry**: `ReplyList[n].EntryList[i]`
- **Start → Entry**: direct index reference
- **Reply categories**: `ReplyListNew[i].Category` drives edge color (Paragon=blue, Renegade=red, Agree, Disagree, Friendly, Hostile)

### 1.4 Data loading flow
```
1. Open .pcc → select BioConversation export
2. Parse SpeakerList / EntryList / ReplyList as raw StructProperty
3. Wrap each node as DialogueNodeExtended (holds StructProperty ref)
4. Create DBox per node → DiagNodeEntry or DiagNodeReply
5. Layout() → position title box, spoken line, input/output connectors
6. CreateConnections() → wire DiagEdEdge between nodes via ID arrays
7. TLK resolution via GlobalFindStrRefbyID() against loaded TLK manager
```

### 1.5 Editing capabilities (out of scope for MVP)
- Drag nodes (saved layouts per conversation)
- Drag output connectors to create links
- Right-click context menus: add / clone / delete nodes
- All edits modify the underlying StructProperty directly

---

## 2. Our Current State

| Component | Status |
|---|---|
| PCC reading + decompression | Done (Python, `src/pcc/`) |
| BioConversation detection | Done |
| Conversation AST parsing | Done (`src/dialogue/conversation_parser.py`) |
| TLK resolution | Done (`src/tlk/`) |
| CLI extractor | Done (`pcc_dialog_extract`) |
| GUI window + tabs | Done (`src/gui/app.py`) |
| File loader panel | Done |
| Conversation list | Done |
| Graph view (ImDrawList) | Done — read-only, manual straight-line edges, click-to-select |
| Detail panel | Done |
| Sugiyama layout engine | Done (`src/gui/graph/layout.py`) — BFS layering + barycenter |

---

## 3. Gap Analysis (vs LEX Dialog Editor)

### 3.1 Graph rendering

| Feature | LEX | Us | Priority |
|---|---|---|---|
| Bezier edge curves | Yes (log-spaced control points) | No (straight lines) | Medium |
| Edge color by reply category | Yes (Paragon/Renegade/etc) | No (all gray) | Medium |
| Node text: speaker + spoken line | Yes (dual-line layout) | Yes (2-line) | Done |
| Node connectors (in/out ports) | Yes (visible drag handles) | No | Low |
| Zoom smoothness | Piccolo native | ImDrawList manual matrix | Acceptable |
| Pan via right-click drag | Yes | Yes | Done |
| Grid background | No | Yes (ours) | Done |

### 3.2 Speaker / reply category coloring

LEX colors reply edges by `EReplyCategory`:
- Paragon Interrupt (blue), Renegade Interrupt (red)
- Agree (dodger blue), Disagree (tomato)
- Friendly (dark blue), Hostile (dark red)

Our AST does not currently expose `EReplyCategory`. The property `Category` exists in `ReplyListNew[i]` but our `conversation_parser.py` does not extract it.

### 3.3 Layout

LEX has 3 auto-layout algorithms: Simple Column, Complex Column, Waterfall. Layouts can be saved per-conversation. We currently have one custom Sugiyama implementation (BFS + barycenter). **Plan**: replace with `igraph` for production-grade Sugiyama + additional algorithms (waterfall via Reingold-Tilford, force-directed via Kamada-Kawai).

### 3.4 Start nodes / Stage directions

LEX renders start nodes (green `DStart` boxes) and stage directions (scripted scene notes). Our AST does not capture start node metadata.

### 3.5 Read/write

LEX is a full editor (property-level read/write). Ours is read-only by design. Adding write support would require a property serialization layer (deferred).

---

## 4. Backend Gaps (Python — affects both CLI and GUI)

These must be implemented in `src/` before or alongside the GUI phases that depend on them.

### CRITICAL

| ID | File(s) | Description | Affects |
|---|---|---|---|
| **B-GAP-1** | `model/ast.py`, `dialogue/conversation_parser.py` | Extract `Category` (EReplyCategory) from `ReplyListNew[i].Category`. Add `category: str \| None` to `ReplyNode`. | Dialog Explorer (reply colors) |
| **B-GAP-2** | `pcc/models.py` | Add `PccPackage.get_exports_by_class() -> dict[str, list[ExportEntry]]` and `list_class_names() -> list[str]` for tree view grouping. | Package Editor tab |
| **B-GAP-3** | `tlk/reader.py`, `tlk/resolver.py` | Add `TlkFile.iter_entries() -> Iterator[tuple[int, str]]` to decode all (StringID, text) pairs. Add `TlkResolver.iter_all_entries()` with DLC priority ordering. | TLK Editor tab |

### HIGH

| ID | File(s) | Description | Affects |
|---|---|---|---|
| **B-GAP-4** | `model/ast.py`, `dialogue/conversation_parser.py` | Parse `m_StartingList` array. Add `StartNode` AST class (id, target_entry_id). Add `starts: list[StartNode]` to `Conversation`. | Dialog Explorer (start nodes) |
| **B-GAP-5** | `pcc/models.py` | Add `PccPackage.get_export_data(export_index) -> bytes` convenience method for raw serial byte access. | Package Editor tab |
| **B-GAP-6** | `tlk/reader.py`, `tlk/resolver.py` | Add `TlkFile.total_entries` property and `TlkFile.string_ids() -> list[int]` (sorted). Add `TlkResolver.total_unique_entries`. | TLK Editor tab |

### MEDIUM

| ID | File(s) | Description | Affects |
|---|---|---|---|
| **B-GAP-7** | `model/ast.py`, `dialogue/conversation_parser.py` | Parse stage directions. Add `StageDirection` AST class. Determine PCC property mechanism first (may be embedded in EntryList struct items). | Dialog Explorer |
| **B-GAP-8** | `model/ast.py`, `dialogue/conversation_parser.py` | Replace `condition_refs: list[str]` with `conditions: list[Condition]` dataclass (func_ref, param, func_name resolved from name table). | Dialog Explorer |
| **B-GAP-9** | `dialogue/conversation_parser.py` | Extract `nDisplayNameStrRef` from speaker structs in semantic path and resolve via TLK during parsing. | Dialog Explorer (speaker names) |
| **B-GAP-10** | `pcc/models.py`, `pcc/unreal_props.py` | Add `PccPackage.inspect_export_properties(export_index) -> list[ParsedProperty]` as a unified property inspector entry point. | Package Editor tab |
| **B-GAP-11** | `tlk/reader.py`, `tlk/resolver.py` | Add `TlkFile.search(query) -> list[tuple[int, str]]` and `TlkResolver.search(query) -> list[...]` for text-content search. | TLK Editor tab |
| **B-GAP-12** | `cli.py` → extract to shared module | Extract Go scanner subprocess logic from CLI into a reusable module callable from both CLI and GUI (background-thread safe). | Cross-cutting (StrRef index) |

### LOW

| ID | File(s) | Description | Affects |
|---|---|---|---|
| **B-GAP-13** | `pcc/models.py` | Convert `iter_exports()` to generator for memory efficiency on large files. | Package Editor tab |
| **B-GAP-14** | `tlk/resolver.py` | Support female stringref resolution toggle in `TlkResolver.resolve()`. | TLK Editor tab |
| **B-GAP-15** | `dialogue/conversation_parser.py` | Extract `nListenerIndex` / listener tag in semantic parsing path (currently only in row-path). | Dialog Explorer |

---

## 5. Implementation Plan

Backend gaps are listed as prerequisites (`B-GAP-N`) so they benefit both CLI and GUI.

### Phase 0 — Foundation (done)
- [x] Dear ImGui window scaffold
- [x] AppState dataclass
- [x] Tab bar (Package Editor / TLK Editor / Dialog Explorer)
- [x] Layout: left sidebar (1/4) + graph view (3/4)

### Phase 1 — File loader & conversation list (done)
- [x] Native file dialogs for .pcc / .tlk / DLC dir
- [x] Load PCC → parse BioConversations → resolve TLK
- [x] Filterable conversation list with tooltips

### Phase 2 — Graph view core (done)
- [x] Sugiyama layout engine (BFS + barycenter)
- [x] ImDrawList node rendering (2-line: speaker + text)
- [x] Straight-line edges with arrowheads
- [x] Zoom (wheel) + pan (right-drag) + click-to-select

### Phase 3 — Detail panel (done)
- [x] Entry node: speaker, listener, StrRef, text, reply links
- [x] Reply node: StrRef, target entry, text, conditions
- [x] Conversation overview: metadata + speaker list

### Phase 4 — Backend: AST enrichment
- [ ] **B-GAP-1**: Extract `Category` from `ReplyListNew`, add to `ReplyNode`
- [ ] **B-GAP-4**: Parse `m_StartingList`, add `StartNode` to AST
- [ ] **B-GAP-7**: Parse stage directions (needs data exploration first)
- [ ] **B-GAP-8**: Structured `Condition` dataclass replacing `condition_refs: list[str]`
- [ ] **B-GAP-9**: Extract speaker display name StrRef in semantic path
- [ ] **B-GAP-15**: Extract listener tag in semantic path

### Phase 5 — Backend: Package Editor support
- [ ] **B-GAP-2**: `get_exports_by_class()` and `list_class_names()`
- [ ] **B-GAP-5**: `get_export_data()` for raw serial bytes
- [ ] **B-GAP-10**: `inspect_export_properties()` unified property inspector
- [ ] **B-GAP-13**: Convert `iter_exports()` to generator

### Phase 6 — Backend: TLK Editor support
- [ ] **B-GAP-3**: `iter_entries()` for batch StringID→text decoding
- [ ] **B-GAP-6**: `total_entries`, `string_ids()` sorted list
- [ ] **B-GAP-11**: `search()` method for text-content search
- [ ] **B-GAP-14**: Female stringref toggle

### Phase 7 — Backend: Cross-cutting
- [ ] **B-GAP-12**: Extract Go scanner invocation into reusable module

### Phase 8 — GUI: Graph polish (needs Phase 4)
- [ ] Bezier edge curves replacing straight lines
- [ ] Edge color by reply category (uses B-GAP-1)
- [ ] Reply node color by category
- [ ] Start node rendering (green boxes, uses B-GAP-4)
- [ ] Fix edge overlapping: parallel arcs for multi-edges

### Phase 9 — GUI: Layout engine → igraph
- [ ] Add `igraph>=0.11` to `pyproject.toml` optional deps
- [ ] Replace `src/gui/graph/layout.py` with igraph-based implementation
- [ ] igraph `layout_sugiyama()` as default
- [ ] Add `layout_reingold_tilford()` for Waterfall mode
- [ ] Layout selector in UI: Sugiyama / Waterfall / Force-Directed
- [ ] Re-layout button
- [ ] Remove hand-written Sugiyama code

### Phase 10 — GUI: Package Editor tab (needs Phase 5)
- [ ] Tree view of exports grouped by class
- [ ] Click export → raw hex view + property tree
- [ ] Property type rendering (Int, Float, String, Object, Array, Struct, Enum)

### Phase 11 — GUI: TLK Editor tab (needs Phase 6)
- [ ] Table view: StringID column + Text column
- [ ] Search/filter by StringID or text content
- [ ] Jump to StringID
- [ ] Male/female toggle

### Phase 12 — QA & hardening
- [ ] Test with ME2 OT: CitHub, CitAsL, Nor, BchLmL
- [ ] Test with LE2 samples
- [ ] Handle malformed / empty conversations gracefully
- [ ] Performance: large conversations (200+ nodes) without frame drops

---

## 6. Library Options for Graph Rendering

### Option A: Keep ImDrawList (current)
- **Pros**: Zero dependencies, full control, same stack
- **Cons**: Manual bezier math, no built-in graph layout, text clipping manual
- **Verdict**: ✅ Keep for MVP. Sufficient for read-only viewer.

### Option B: `pygraphviz` / `graphviz`
- **Pros**: Production-grade Sugiyama, DOT input, SVG/PNG export
- **Cons**: Requires Graphviz binary install, not interactive, render to static image
- **Verdict**: ❌ Not suitable for interactive editor.

### Option C: `networkx` + `matplotlib`
- **Pros**: Rich graph algorithms, matplotlib for rendering
- **Cons**: Matplotlib embedding in ImGui is painful, no zoom/pan, sluggish
- **Verdict**: ❌ Not built for real-time interaction.

### Option D: `igraph` (python-igraph)
- **Pros**: Fast C core, many layout algorithms (Sugiyama, Reingold-Tilford, Kamada-Kawai, DrL). Zero external binaries. Returns simple coordinate arrays → direct feed to `to_screen()`.
- **Cons**: Layout only, no rendering (ImDrawList handles that). Installation is a single `pip install igraph`.
- **Verdict**: ✅ **Selected**. Replaces our custom Sugiyama. Enables Waterfall and Force-Directed with minimal code.

### Option E: Piccolo.NET (C# via pythonnet)
- **Pros**: Exactly what LEX uses, mature zoomable canvas
- **Cons**: Cross-language bridge adds complexity, Windows-only, distribution pain
- **Verdict**: ❌ Not worth the interop cost for a Python app.

### Recommendation
**ImDrawList** for rendering + **igraph** for layout. ImDrawList gives full control over bezier curves, color-coded edges, and text. igraph handles all graph algorithms with a C core, no external binaries, single `pip install`. The integration is trivial: build an `igraph.Graph`, call `layout_sugiyama()`, feed positions to `to_screen()`.

### Dependencies to add
```
igraph>=0.11
```

---

## 7. Immediate Next Steps

**Backend first** (benefits both CLI and GUI):

1. **B-GAP-1** — Add `category` field to `ReplyNode`, extract `Category` from `ReplyListNew` in parser
2. **B-GAP-2** — Add `get_exports_by_class()` to `PccPackage`
3. **B-GAP-3** — Add `iter_entries()` to `TlkFile` / `TlkResolver`
4. **B-GAP-4** — Parse `m_StartingList`, add `StartNode` to AST

**Then GUI phases:**

5. Phase 8 — Bezier edges + reply category coloring (uses B-GAP-1)
6. Phase 9 — igraph layout engine
7. Phase 10 — Package Editor tab (uses B-GAP-2, B-GAP-5, B-GAP-10)
8. Phase 11 — TLK Editor tab (uses B-GAP-3, B-GAP-6, B-GAP-11)
