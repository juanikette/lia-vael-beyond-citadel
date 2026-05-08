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
from tlk import TlkFormatError, build_tlk_resolver, resolve_conversations_tlk
from validation import write_phase3_batch_report, write_phase3_report


GAMES = ("me1", "me2", "me3", "le1", "le2", "le3")


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
