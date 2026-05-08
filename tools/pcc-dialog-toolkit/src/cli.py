from __future__ import annotations

import argparse
import json
from pathlib import Path

from dialogue import (
    parse_all_bioconversation_stubs,
    parse_all_bioconversation_stubs_resilient,
)
from pcc import PccFormatError, read_pcc
from serialize import build_output_payload, validate_output_payload, write_output_json
from tlk import TlkFormatError, build_tlk_resolver, find_dlc_tlk_files, read_tlk, resolve_conversations_tlk, resolve_tlk_string
from validation import write_phase3_batch_report, write_phase3_report


GAMES = ("me1", "me2", "me3", "le1", "le2", "le3")


def _contains_query(value: str | None, query: str) -> bool:
    if not value:
        return False
    return query.casefold() in value.casefold()


def _conversation_match_reasons(conversation, query: str) -> list[str]:
    reasons: list[str] = []

    if _contains_query(conversation.id, query):
        reasons.append("conversation_id")

    for entry in conversation.entries:
        if _contains_query(entry.speaker_tag, query):
            reasons.append("entry_speaker_tag")
            break
    for entry in conversation.entries:
        if _contains_query(entry.listener_tag, query):
            reasons.append("entry_listener_tag")
            break
    for entry in conversation.entries:
        if _contains_query(entry.line_text, query):
            reasons.append("entry_line_text")
            break

    for reply in conversation.replies:
        if _contains_query(reply.line_text, query):
            reasons.append("reply_line_text")
            break

    for speaker in conversation.speakers:
        if _contains_query(speaker.tag, query):
            reasons.append("speaker_tag")
            break
        if _contains_query(speaker.display_name, query):
            reasons.append("speaker_display_name")
            break

    return reasons


def _conversation_lia_vael_context(conversation) -> tuple[int, list[str], list[str]]:
    markers = {
        "quarian": 3,
        "migrant fleet": 3,
        "pilgrimage": 2,
        "citadel": 1,
        "zakera": 2,
        "c-sec": 2,
        "volus": 2,
        "contract": 1,
        "merchant": 1,
        "accused": 1,
        "framed": 1,
    }

    fields: list[str] = [conversation.id or ""]
    for entry in conversation.entries:
        fields.extend([entry.speaker_tag or "", entry.listener_tag or "", entry.line_text or ""])
    for reply in conversation.replies:
        fields.append(reply.line_text or "")
    for speaker in conversation.speakers:
        fields.extend([speaker.tag or "", speaker.display_name or ""])

    blob = "\n".join(fields)
    low = blob.casefold()

    score = 0
    hits: list[str] = []
    for keyword, weight in markers.items():
        if keyword in low:
            score += weight
            hits.append(keyword)

    snippets: list[str] = []
    for entry in conversation.entries:
        text = entry.line_text or ""
        text_low = text.casefold()
        if any(keyword in text_low for keyword in hits):
            snippets.append(text)
            if len(snippets) >= 3:
                break
    for reply in conversation.replies:
        if len(snippets) >= 3:
            break
        text = reply.line_text or ""
        text_low = text.casefold()
        if any(keyword in text_low for keyword in hits):
            snippets.append(text)

    return score, sorted(set(hits)), snippets


def _find_strref_usages(conversations, targets: set[int]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for conversation in conversations:
        for entry in conversation.entries:
            if entry.line_strref in targets:
                rows.append(
                    {
                        "kind": "entry",
                        "conversation_id": conversation.id,
                        "export_index": conversation.export_index,
                        "node_id": entry.id,
                        "strref": entry.line_strref,
                        "line_text": entry.line_text,
                    }
                )
        for reply in conversation.replies:
            if reply.line_strref in targets:
                rows.append(
                    {
                        "kind": "reply",
                        "conversation_id": conversation.id,
                        "export_index": conversation.export_index,
                        "node_id": reply.id,
                        "strref": reply.line_strref,
                        "line_text": reply.line_text,
                    }
                )
    return rows


def _infer_biogame_root_from_tlk(base_tlk: Path) -> Path | None:
    # Expected: <BioGame>/CookedPC/BIOGame_INT.tlk
    cooked = base_tlk.parent
    if cooked.name.casefold().startswith("cookedpc") and cooked.parent.exists():
        return cooked.parent
    return None


def _load_candidate_index(path: Path) -> list[Path]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("candidates")
    if not isinstance(raw, list):
        raise ValueError("Candidate index must contain a 'candidates' array")
    rows: list[Path] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            rows.append(Path(item))
    return rows


def _build_evidence_report(
    *,
    base_tlk: Path,
    dlc_dir: Path,
    queries: list[str],
    candidate_index_path: Path | None = None,
) -> dict[str, object]:
    normalized_queries = [item.strip().casefold() for item in queries if item.strip()]
    if not normalized_queries:
        raise ValueError("At least one non-empty query is required")

    tlk_paths = [base_tlk] + find_dlc_tlk_files(dlc_dir)
    tlk_hits: list[dict[str, object]] = []
    target_strrefs: set[int] = set()
    for tlk_path in tlk_paths:
        tlk_file = read_tlk(tlk_path)
        for string_id in tlk_file.male_stringrefs:
            value = resolve_tlk_string(tlk_file, string_id, male=True)
            if value is None:
                continue
            low = value.casefold()
            hit_queries = [query for query in normalized_queries if query in low]
            if not hit_queries:
                continue
            target_strrefs.add(int(string_id))
            tlk_hits.append(
                {
                    "tlk": str(tlk_path),
                    "strref": int(string_id),
                    "queries": hit_queries,
                    "text": value,
                }
            )

    biogame_root = _infer_biogame_root_from_tlk(base_tlk)
    if biogame_root is None:
        raise ValueError("Could not infer BioGame root from --tlk path")

    pcc_files = sorted((biogame_root / "CookedPC").glob("*.pcc")) + sorted(dlc_dir.rglob("*.pcc"))
    candidate_pcc_files: list[Path] = []
    pcc_errors: list[dict[str, str]] = []
    if candidate_index_path is not None:
        indexed = _load_candidate_index(candidate_index_path)
        for item in indexed:
            if item.exists() and item.is_file() and item.suffix.casefold() == ".pcc":
                candidate_pcc_files.append(item)
    else:
        target_signatures = {
            strref: strref.to_bytes(4, byteorder="little", signed=True)
            for strref in sorted(target_strrefs)
        }
        for pcc_path in pcc_files:
            try:
                blob = pcc_path.read_bytes()
            except OSError as exc:
                pcc_errors.append({"file": str(pcc_path), "stage": "read_bytes", "error": str(exc)})
                continue
            if not target_signatures:
                continue
            if any(signature in blob for signature in target_signatures.values()):
                candidate_pcc_files.append(pcc_path)

    usages: list[dict[str, object]] = []
    raw_export_hits: list[dict[str, object]] = []
    conversations_total = 0

    for pcc_path in candidate_pcc_files:
        try:
            package = read_pcc(pcc_path)
        except (PccFormatError, OSError) as exc:
            pcc_errors.append({"file": str(pcc_path), "stage": "read_pcc", "error": str(exc)})
            continue

        if target_strrefs:
            export_hits = package.scan_exports_for_i32_values(
                target_strrefs,
                class_name_contains=("Conversation", "Sequence", "SeqAct", "Plot"),
            )
            for hit in export_hits:
                hit["file"] = str(pcc_path)
                raw_export_hits.append(hit)

        if not package.iter_exports(class_name="BioConversation"):
            continue

        try:
            conversations = parse_all_bioconversation_stubs(package)
        except (PccFormatError, OSError) as exc:
            pcc_errors.append({"file": str(pcc_path), "stage": "parse_conversations", "error": str(exc)})
            continue
        conversations_total += len(conversations)
        rows = _find_strref_usages(conversations, target_strrefs)
        for row in rows:
            row["file"] = str(pcc_path)
            usages.append(row)

    return {
        "report": "dialogue-evidence",
        "queries": normalized_queries,
        "summary": {
            "tlk_files_scanned": len(tlk_paths),
            "tlk_hits": len(tlk_hits),
            "target_strrefs": len(target_strrefs),
            "pcc_files_scanned": len(pcc_files),
            "candidate_pcc_files": len(candidate_pcc_files),
            "candidate_source": "index" if candidate_index_path is not None else "python_prefilter",
            "conversations_total": conversations_total,
            "strref_usages": len(usages),
            "raw_export_hits": len(raw_export_hits),
            "pcc_errors": len(pcc_errors),
        },
        "tlk_hits": tlk_hits,
        "strref_usages": usages,
        "raw_export_hits": raw_export_hits,
        "errors": pcc_errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pcc_dialog_extract",
        description="Extracts BioConversation dialogue from PCC files (MVP in progress).",
    )
    parser.add_argument("input_pcc", nargs="?", help="Input .pcc file path")
    parser.add_argument("--game", choices=GAMES, help="Target game profile")
    parser.add_argument("--tlk", help="Base TLK path (BIOGame_INT.tlk)")
    parser.add_argument("--dlc-dir", help="DLC directory path")
    parser.add_argument("-o", "--output", help="Output JSON file path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-printed JSON output")
    parser.add_argument(
        "--list-bioconversations",
        action="store_true",
        help="List BioConversation exports with minimal metadata",
    )
    parser.add_argument(
        "--inspect-bioconversation-properties",
        action="store_true",
        help="Inspect key BioConversation properties (EntryList/ReplyList/SpeakerList)",
    )
    parser.add_argument(
        "--inspect-bioconversation-owners",
        action="store_true",
        help="Inspect BioConversation owner ObjectProperty references",
    )
    parser.add_argument(
        "--find-reference",
        action="append",
        default=[],
        help=(
            "Find BioConversation references by substring in conversation id, "
            "speaker/listener tags, and resolved line text. Repeatable."
        ),
    )
    parser.add_argument(
        "--find-context-profile",
        choices=("lia-vael",),
        help="Find contextual matches using a built-in profile.",
    )
    parser.add_argument(
        "--context-min-score",
        type=int,
        default=4,
        help="Minimum context score threshold for --find-context-profile (default: 4).",
    )
    parser.add_argument(
        "--scan-tlk-reference",
        action="append",
        default=[],
        help="Search base TLK and DLC TLKs for one or more substrings. Repeatable.",
    )
    parser.add_argument(
        "--trace-strref-usage",
        type=int,
        action="append",
        default=[],
        help="Trace one or more StrRef IDs in parsed BioConversation entries/replies. Repeatable.",
    )
    parser.add_argument(
        "--lia-vael-evidence-report",
        help="Write a consolidated Lia'Vael TLK+StrRef evidence JSON report.",
    )
    parser.add_argument(
        "--evidence-report",
        help="Write a consolidated TLK+StrRef evidence JSON report for custom queries.",
    )
    parser.add_argument(
        "--evidence-query",
        action="append",
        default=[],
        help="Query used by --evidence-report. Repeatable.",
    )
    parser.add_argument(
        "--candidate-index",
        help="Optional JSON file with precomputed PCC candidates (for example generated by Go scanner).",
    )
    parser.add_argument(
        "--dump-bioconversation-property-tags",
        action="store_true",
        help="Dump all top-level property tags detected in BioConversation",
    )
    parser.add_argument(
        "--dump-bioconversation-stub",
        action="store_true",
        help="Generate BioConversation AST stubs",
    )
    parser.add_argument(
        "--dump-bioconversation-row-payloads",
        action="store_true",
        help="Dump detected bootstrap rows for Entry/Reply/Speaker",
    )
    parser.add_argument(
        "--validate-bioconversation-stubs",
        action="store_true",
        help="Validate internal consistency of AST stubs per conversation",
    )
    parser.add_argument(
        "--strict-validation",
        action="store_true",
        help="Return exit code 3 when invalid conversations or needs_schema_review are present",
    )
    parser.add_argument(
        "--phase3-report",
        help="Write consolidated Phase 3 validation JSON report",
    )
    parser.add_argument(
        "--phase3-batch-dir",
        help="Directory used to generate a Phase 3 batch report across multiple PCC files",
    )
    parser.add_argument(
        "--phase3-batch-glob",
        default="*.pcc",
        help="Glob pattern for batch report (default: *.pcc)",
    )
    parser.add_argument(
        "--phase3-batch-report",
        help="Output JSON path for Phase 3 batch report",
    )
    parser.add_argument("--version", action="store_true", help="Show current version")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("pcc-dialog-toolkit 0.1.0")
        return 0

    if args.phase3_batch_report:
        if not args.phase3_batch_dir:
            parser.error("--phase3-batch-report requires --phase3-batch-dir")
        batch_dir = Path(args.phase3_batch_dir)
        if not batch_dir.exists() or not batch_dir.is_dir():
            parser.error(f"Batch directory does not exist: {batch_dir}")
        files = sorted(batch_dir.glob(args.phase3_batch_glob))
        if not files:
            parser.error(f"No files matched batch glob: {args.phase3_batch_glob}")
        output_path = write_phase3_batch_report(files, args.phase3_batch_report, pretty=args.pretty)
        print(f"Phase 3 batch report written: {output_path}")
        return 0

    if args.lia_vael_evidence_report:
        if not args.tlk:
            parser.error("--lia-vael-evidence-report requires --tlk")
        if not args.dlc_dir:
            parser.error("--lia-vael-evidence-report requires --dlc-dir")

        tlk_path = Path(args.tlk)
        dlc_path = Path(args.dlc_dir)
        if not tlk_path.exists() or not tlk_path.is_file():
            parser.error(f"Base TLK does not exist: {tlk_path}")
        if not dlc_path.exists() or not dlc_path.is_dir():
            parser.error(f"DLC directory does not exist: {dlc_path}")

        report = _build_evidence_report(
            base_tlk=tlk_path,
            dlc_dir=dlc_path,
            queries=["lia'vael", "liavael", "vael", "lia vael"],
            candidate_index_path=Path(args.candidate_index) if args.candidate_index else None,
        )
        output_path = Path(args.lia_vael_evidence_report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2 if args.pretty else None, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Lia'Vael evidence report written: {output_path}")
        print(
            "Evidence summary: "
            f"tlk_hits={report['summary']['tlk_hits']} "
            f"target_strrefs={report['summary']['target_strrefs']} "
            f"strref_usages={report['summary']['strref_usages']} "
            f"raw_export_hits={report['summary']['raw_export_hits']}"
        )
        return 0

    if args.evidence_report:
        if not args.tlk:
            parser.error("--evidence-report requires --tlk")
        if not args.dlc_dir:
            parser.error("--evidence-report requires --dlc-dir")
        if not args.evidence_query:
            parser.error("--evidence-report requires at least one --evidence-query")

        tlk_path = Path(args.tlk)
        dlc_path = Path(args.dlc_dir)
        if not tlk_path.exists() or not tlk_path.is_file():
            parser.error(f"Base TLK does not exist: {tlk_path}")
        if not dlc_path.exists() or not dlc_path.is_dir():
            parser.error(f"DLC directory does not exist: {dlc_path}")

        report = _build_evidence_report(
            base_tlk=tlk_path,
            dlc_dir=dlc_path,
            queries=[str(item) for item in args.evidence_query],
            candidate_index_path=Path(args.candidate_index) if args.candidate_index else None,
        )
        output_path = Path(args.evidence_report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2 if args.pretty else None, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Evidence report written: {output_path}")
        print(
            "Evidence summary: "
            f"tlk_hits={report['summary']['tlk_hits']} "
            f"target_strrefs={report['summary']['target_strrefs']} "
            f"strref_usages={report['summary']['strref_usages']} "
            f"raw_export_hits={report['summary']['raw_export_hits']}"
        )
        return 0

    if not args.input_pcc:
        parser.print_help()
        return 0

    input_path = Path(args.input_pcc)
    if not input_path.exists():
        parser.error(f"PCC file does not exist: {input_path}")

    try:
        package = read_pcc(input_path)
    except PccFormatError as exc:
        parser.exit(status=2, message=f"Error reading PCC: {exc}\n")

    print(f"PCC: {input_path}")
    print(
        "Header: "
        f"unreal={package.header.unreal_version} "
        f"licensee={package.header.licensee_version}"
    )
    print(
        "Tables: "
        f"names={len(package.names)} "
        f"imports={len(package.imports)} "
        f"exports={len(package.exports)}"
    )
    if args.list_bioconversations:
        conversations = package.list_bioconversations()
        print(f"BioConversation exports: {len(conversations)}")
        for row in conversations:
            print(
                f"- idx={row['index']} "
                f"name={row['name']} "
                f"class={row['class']} "
                f"offset={row['offset']} "
                f"size={row['size']}"
            )

    if args.inspect_bioconversation_properties:
        rows = package.inspect_bioconversation_properties()
        print(f"BioConversation property-inspection exports: {len(rows)}")
        for row in rows:
            print(f"- idx={row['index']} name={row['name']}")
            for prop in row["properties"]:
                print(
                    "  "
                    f"prop={prop['name']} "
                    f"type={prop['type']} "
                    f"size={prop['size']} "
                    f"array_index={prop['array_index']} "
                    f"value_offset={prop['value_offset']}"
                )

    if args.inspect_bioconversation_owners:
        rows = package.inspect_bioconversation_owners()
        print(f"BioConversation owner-inspection exports: {len(rows)}")
        for row in rows:
            owner = row["owner"]
            if owner is None:
                print(
                    f"- idx={row['index']} "
                    f"name={row['name']} "
                    f"owner_property={row['owner_property']} "
                    f"owner_ref={row['owner_ref']} "
                    "owner_kind=None owner_name=None"
                )
                continue
            print(
                f"- idx={row['index']} "
                f"name={row['name']} "
                f"owner_property={row['owner_property']} "
                f"owner_ref={row['owner_ref']} "
                f"owner_kind={owner.get('kind')} "
                f"owner_name={owner.get('name')} "
                f"owner_class={owner.get('class')}"
            )

    if args.dump_bioconversation_stub:
        conversations = parse_all_bioconversation_stubs(package)
        if args.tlk:
            tlk_path = Path(args.tlk)
            if not tlk_path.exists() or not tlk_path.is_file():
                parser.error(f"Base TLK does not exist: {tlk_path}")
            dlc_dir = None
            if args.dlc_dir:
                dlc_path = Path(args.dlc_dir)
                if not dlc_path.exists() or not dlc_path.is_dir():
                    parser.error(f"DLC directory does not exist: {dlc_path}")
                dlc_dir = dlc_path
            try:
                resolver = build_tlk_resolver(base_tlk_path=tlk_path, dlc_dir=dlc_dir)
            except TlkFormatError as exc:
                parser.exit(status=2, message=f"Error reading TLK: {exc}\n")
            conversations = resolve_conversations_tlk(conversations, resolver)
        conversations_payload = [row.to_dict() for row in conversations]
        if args.pretty:
            print(json.dumps(conversations_payload, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(conversations_payload, ensure_ascii=False))

    if args.find_reference:
        conversations = parse_all_bioconversation_stubs(package)
        if args.tlk:
            tlk_path = Path(args.tlk)
            if not tlk_path.exists() or not tlk_path.is_file():
                parser.error(f"Base TLK does not exist: {tlk_path}")
            dlc_dir = None
            if args.dlc_dir:
                dlc_path = Path(args.dlc_dir)
                if not dlc_path.exists() or not dlc_path.is_dir():
                    parser.error(f"DLC directory does not exist: {dlc_path}")
                dlc_dir = dlc_path
            try:
                resolver = build_tlk_resolver(base_tlk_path=tlk_path, dlc_dir=dlc_dir)
            except TlkFormatError as exc:
                parser.exit(status=2, message=f"Error reading TLK: {exc}\n")
            conversations = resolve_conversations_tlk(conversations, resolver)

        queries = [str(item).strip() for item in args.find_reference if str(item).strip()]
        if not queries:
            parser.error("--find-reference requires a non-empty value")

        print(f"Reference queries: {', '.join(queries)}")
        if not args.tlk:
            print("Note: --tlk not provided; line_text matching may be limited.")

        matched_rows: list[tuple[object, dict[str, list[str]]]] = []
        for conversation in conversations:
            reasons_by_query: dict[str, list[str]] = {}
            for query in queries:
                reasons = _conversation_match_reasons(conversation, query)
                if reasons:
                    reasons_by_query[query] = reasons
            if reasons_by_query:
                matched_rows.append((conversation, reasons_by_query))

        print(f"BioConversation matches: {len(matched_rows)}")
        for conversation, reasons_by_query in matched_rows:
            parts = []
            for query in queries:
                reasons = reasons_by_query.get(query)
                if reasons:
                    parts.append(f"{query}=>{'+'.join(reasons)}")
            reason_text = "; ".join(parts)
            print(
                f"- idx={conversation.export_index} "
                f"name={conversation.id} "
                f"parse_mode={conversation.parse_mode} "
                f"matches={reason_text}"
            )

    if args.find_context_profile:
        conversations = parse_all_bioconversation_stubs(package)
        if args.tlk:
            tlk_path = Path(args.tlk)
            if not tlk_path.exists() or not tlk_path.is_file():
                parser.error(f"Base TLK does not exist: {tlk_path}")
            dlc_dir = None
            if args.dlc_dir:
                dlc_path = Path(args.dlc_dir)
                if not dlc_path.exists() or not dlc_path.is_dir():
                    parser.error(f"DLC directory does not exist: {dlc_path}")
                dlc_dir = dlc_path
            try:
                resolver = build_tlk_resolver(base_tlk_path=tlk_path, dlc_dir=dlc_dir)
            except TlkFormatError as exc:
                parser.exit(status=2, message=f"Error reading TLK: {exc}\n")
            conversations = resolve_conversations_tlk(conversations, resolver)

        if not args.tlk:
            print("Note: --tlk not provided; context matching may miss text evidence.")

        print(
            f"Context profile: {args.find_context_profile} "
            f"(min_score={args.context_min_score})"
        )
        matched: list[tuple[object, int, list[str], list[str]]] = []
        for conversation in conversations:
            if args.find_context_profile == "lia-vael":
                score, hits, snippets = _conversation_lia_vael_context(conversation)
            else:
                score, hits, snippets = 0, [], []
            if score >= args.context_min_score:
                matched.append((conversation, score, hits, snippets))

        matched.sort(key=lambda item: item[1], reverse=True)
        print(f"Context matches: {len(matched)}")
        for conversation, score, hits, snippets in matched:
            snippet = snippets[0] if snippets else None
            print(
                f"- idx={conversation.export_index} "
                f"name={conversation.id} "
                f"score={score} "
                f"hits={'+'.join(hits)} "
                f"sample_line={snippet}"
            )

    if args.scan_tlk_reference:
        from tlk import find_dlc_tlk_files, read_tlk, resolve_tlk_string

        if not args.tlk:
            parser.error("--scan-tlk-reference requires --tlk")

        base_tlk = Path(args.tlk)
        if not base_tlk.exists() or not base_tlk.is_file():
            parser.error(f"Base TLK does not exist: {base_tlk}")

        queries = [str(item).strip() for item in args.scan_tlk_reference if str(item).strip()]
        if not queries:
            parser.error("--scan-tlk-reference requires a non-empty value")

        tlk_paths = [base_tlk]
        if args.dlc_dir:
            dlc_path = Path(args.dlc_dir)
            if not dlc_path.exists() or not dlc_path.is_dir():
                parser.error(f"DLC directory does not exist: {dlc_path}")
            tlk_paths.extend(find_dlc_tlk_files(dlc_path))

        print(f"TLK reference queries: {', '.join(queries)}")
        print(f"TLK files scanned: {len(tlk_paths)}")

        total_matches = 0
        for tlk_path in tlk_paths:
            tlk_file = read_tlk(tlk_path)
            tlk_rows = []
            for string_id in tlk_file.male_stringrefs:
                value = resolve_tlk_string(tlk_file, string_id, male=True)
                if value is None:
                    continue
                lower = value.casefold()
                hit_queries = [query for query in queries if query.casefold() in lower]
                if hit_queries:
                    tlk_rows.append((string_id, hit_queries, value))
            if not tlk_rows:
                continue

            total_matches += len(tlk_rows)
            print(f"- tlk={tlk_path} matches={len(tlk_rows)}")
            for string_id, hit_queries, value in tlk_rows:
                print(f"  strref={string_id} queries={'+'.join(hit_queries)} text={value}")
        print(f"TLK matches total: {total_matches}")

    if args.trace_strref_usage:
        targets = {int(item) for item in args.trace_strref_usage if int(item) >= 0}
        if not targets:
            parser.error("--trace-strref-usage requires at least one non-negative integer")

        conversations = parse_all_bioconversation_stubs(package)
        if args.tlk:
            tlk_path = Path(args.tlk)
            if not tlk_path.exists() or not tlk_path.is_file():
                parser.error(f"Base TLK does not exist: {tlk_path}")
            dlc_dir = None
            if args.dlc_dir:
                dlc_path = Path(args.dlc_dir)
                if not dlc_path.exists() or not dlc_path.is_dir():
                    parser.error(f"DLC directory does not exist: {dlc_path}")
                dlc_dir = dlc_path
            try:
                resolver = build_tlk_resolver(base_tlk_path=tlk_path, dlc_dir=dlc_dir)
            except TlkFormatError as exc:
                parser.exit(status=2, message=f"Error reading TLK: {exc}\n")
            conversations = resolve_conversations_tlk(conversations, resolver)

        rows = _find_strref_usages(conversations, targets)
        print(f"StrRef targets: {', '.join(str(item) for item in sorted(targets))}")
        print(f"StrRef usage matches: {len(rows)}")
        for row in rows:
            print(
                f"- kind={row['kind']} "
                f"strref={row['strref']} "
                f"idx={row['export_index']} "
                f"name={row['conversation_id']} "
                f"node={row['node_id']} "
                f"text={row['line_text']}"
            )

    if args.output:
        conversations, errors = parse_all_bioconversation_stubs_resilient(package)
        if args.tlk:
            tlk_path = Path(args.tlk)
            if not tlk_path.exists() or not tlk_path.is_file():
                parser.error(f"Base TLK does not exist: {tlk_path}")
            dlc_dir = None
            if args.dlc_dir:
                dlc_path = Path(args.dlc_dir)
                if not dlc_path.exists() or not dlc_path.is_dir():
                    parser.error(f"DLC directory does not exist: {dlc_path}")
                dlc_dir = dlc_path
            try:
                resolver = build_tlk_resolver(base_tlk_path=tlk_path, dlc_dir=dlc_dir)
            except TlkFormatError as exc:
                parser.exit(status=2, message=f"Error reading TLK: {exc}\n")
            conversations = resolve_conversations_tlk(conversations, resolver)

        payload = build_output_payload(
            input_pcc=str(input_path),
            game=args.game,
            conversations=conversations,
            errors=errors,
        )
        validate_output_payload(payload)
        output_path = write_output_json(output_path=args.output, payload=payload, pretty=args.pretty)
        print(f"Output JSON written: {output_path}")

        warning_total = int(payload["summary"]["warnings_total"])
        if warning_total > 0:
            print(f"Warnings detected: {warning_total}")
            for conversation in conversations:
                if conversation.warnings:
                    print(
                        f"- warning id={conversation.id} "
                        f"export_index={conversation.export_index} "
                        f"warnings={';'.join(conversation.warnings)}"
                    )
        if errors:
            print(f"Conversations with errors: {len(errors)}")
            for item in errors:
                print(
                    f"- error id={item.get('id')} "
                    f"export_index={item.get('export_index')} "
                    f"detail={item.get('error')}"
                )

    if args.dump_bioconversation_row_payloads:
        payloads = package.inspect_bioconversation_row_payloads()
        if args.pretty:
            print(json.dumps(payloads, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(payloads, ensure_ascii=False))

    if args.dump_bioconversation_property_tags:
        tags = package.inspect_bioconversation_property_tags()
        if args.pretty:
            print(json.dumps(tags, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(tags, ensure_ascii=False))

    if args.phase3_report:
        output_path = write_phase3_report(input_path, args.phase3_report, pretty=args.pretty)
        print(f"Phase 3 report written: {output_path}")

    if args.validate_bioconversation_stubs:
        report = package.validate_bioconversation_stubs()
        summary = package.summarize_bioconversation_validation()
        if args.pretty:
            print(json.dumps({"summary": summary, "items": report}, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"summary": summary, "items": report}, ensure_ascii=False))

        if args.strict_validation and (
            int(summary.get("invalid", 0)) > 0 or int(summary.get("needs_schema_review", 0)) > 0
        ):
            return 3

    if args.strict_validation and not args.validate_bioconversation_stubs:
        parser.error("--strict-validation requires --validate-bioconversation-stubs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
