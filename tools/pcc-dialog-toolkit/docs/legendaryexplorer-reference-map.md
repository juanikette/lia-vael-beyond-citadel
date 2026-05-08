# LegendaryExplorer Reference Map

This file records which LegendaryExplorer components are used as the technical baseline.

Repository:
- https://github.com/ME3Tweaks/LegendaryExplorer/

## Phase 0

- Goal: define the consultation and traceability practice per phase.
- Status: initialized.

### Areas to consult in upcoming phases

- PCC package reading (header, names, imports, exports).
- Conversation structures (`BioConversation`, relevant properties).
- TLK reading and DLC priority/override logic.

### Logging rule

When closing each phase, add here:
- LEX file/class consulted,
- toolkit decision made,
- relevant OT vs LE difference detected (if applicable).

## Phase 1

- LEX file/class consulted: `LegendaryExplorerCore/Packages/MEPackage.cs`.
- Toolkit decision: keep minimal defensive parsing for header and base tables, without lazy loading or compression support at this phase.
- OT vs LE difference detected: header format shares base offsets for names/imports/exports; platform/compression variations are deferred to later phases.

## Phase 2

- LEX file/class consulted: `LegendaryExplorerCore/Packages/MEPackage.cs` and `LegendaryExplorerCore/Packages/ImportEntry.cs`.
- Toolkit decision: detect `BioConversation` by resolving export `class_index` to imports and mapping `object_name`/`class_name` through the name table.
- OT vs LE difference detected: class-based detection using import/export index logic remains stable for validated profiles (ME2 OT and LE2).

## Phase 3 (bootstrap)

- LEX file/class consulted: `LegendaryExplorerCore/Packages/MEPackage.cs` (export data reading and high-level property stream structure).
- Toolkit decision: implement a minimal property-tag parser to inspect `EntryList`, `ReplyList`, `SpeakerList` before building the full AST.
- OT vs LE difference detected: in this bootstrap, base property-tag framing for arrays works on ME2 OT fixtures; additional validation on real LE2 samples is deferred to formal phase closure.

## Phase 4 (start)

- LEX file/class consulted: `LegendaryExplorerCore/TLK/ME2ME3/ME2ME3TLKBase.cs`, `LegendaryExplorerCore/TLK/ME2ME3/ME2ME3TalkFile.cs`, `LegendaryExplorerCore/TLK/ME2ME3/ME2ME3LazyTLK.cs`, `LegendaryExplorerCore/TLK/TLKBitArray.cs`, `LegendaryExplorerCore/TLK/ME2TalkFiles.cs`.
- Toolkit decision: implement a ME2/ME3 TLK reader compatible with header + `StringID/BitOffset` table + Huffman tree, and resolve `StrRef` on AST with DLC priority by `MountPriority` and base TLK fallback.
- OT vs LE difference detected: for lookup flow, precedence order by loaded list and shared TLK format in ME2/LE2 enables a common initial path; LE1/ME1 cases (different format) and expanded real-sample validation remain pending.

## Phase 5

- LEX file/class consulted: `LegendaryExplorerCore/Packages/MEPackage.cs` (review of export structure and output conventions for traceability).
- Toolkit decision: introduce versioned JSON output (`schema_version`) with aggregated `summary` and per-conversation errors without aborting the full file.
- OT vs LE difference detected: no additional format changes were detected in this phase (focus on serializer/CLI and pipeline resilience).

## Phase 6 (QA in progress)

- LEX file/class consulted: `LegendaryExplorerCore/Packages/MEPackage.cs`, `LegendaryExplorerCore/TLK/ME2ME3/ME2ME3TalkFile.cs`, `LegendaryExplorerCore/TLK/ME2TalkFiles.cs`.
- Toolkit decision: validate `StrRef`, resolved text, and node links per sample against LEX baseline, preserving evidence per profile (`OT`/`LE2`).
- OT vs LE difference detected: OT validation is in progress; LE2 validation remains pending completion with available local corpus.
