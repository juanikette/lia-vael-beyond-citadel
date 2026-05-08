from __future__ import annotations

import argparse
import json
from pathlib import Path

from pcc_dialog_toolkit.pcc import PccFormatError, read_pcc
from pcc_dialog_toolkit.validation import write_phase3_batch_report, write_phase3_report


GAMES = ("me1", "me2", "me3", "le1", "le2", "le3")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pcc_dialog_extract",
        description="Extrae dialogos BioConversation desde PCC (MVP en desarrollo).",
    )
    parser.add_argument("input_pcc", nargs="?", help="Ruta al archivo .pcc de entrada")
    parser.add_argument("--game", choices=GAMES, help="Juego objetivo")
    parser.add_argument("--tlk", help="Ruta al TLK base (BIOGame_INT.tlk)")
    parser.add_argument("--dlc-dir", help="Ruta al directorio DLC")
    parser.add_argument("-o", "--output", help="Archivo JSON de salida")
    parser.add_argument("--pretty", action="store_true", help="Salida JSON legible")
    parser.add_argument(
        "--list-bioconversations",
        action="store_true",
        help="Lista exports BioConversation con metadata minima",
    )
    parser.add_argument(
        "--inspect-bioconversation-properties",
        action="store_true",
        help="Inspecciona propiedades clave de BioConversation (EntryList/ReplyList/SpeakerList)",
    )
    parser.add_argument(
        "--dump-bioconversation-stub",
        action="store_true",
        help="Genera AST stub de conversaciones BioConversation",
    )
    parser.add_argument(
        "--dump-bioconversation-row-payloads",
        action="store_true",
        help="Vuelca filas bootstrap detectadas para Entry/Reply/Speaker",
    )
    parser.add_argument(
        "--validate-bioconversation-stubs",
        action="store_true",
        help="Valida consistencia interna de AST stubs por conversacion",
    )
    parser.add_argument(
        "--strict-validation",
        action="store_true",
        help="Devuelve exit code 3 si hay conversacion invalida o needs_schema_review",
    )
    parser.add_argument(
        "--phase3-report",
        help="Escribe reporte JSON consolidado de validacion Fase 3",
    )
    parser.add_argument(
        "--phase3-batch-dir",
        help="Directorio para generar reporte batch Fase 3 sobre multiples PCC",
    )
    parser.add_argument(
        "--phase3-batch-glob",
        default="*.pcc",
        help="Patron glob para batch report (default: *.pcc)",
    )
    parser.add_argument(
        "--phase3-batch-report",
        help="Ruta JSON de salida para reporte batch Fase 3",
    )
    parser.add_argument("--version", action="store_true", help="Muestra la version actual")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("pcc-dialog-toolkit 0.1.0")
        return 0

    if args.phase3_batch_report:
        if not args.phase3_batch_dir:
            parser.error("--phase3-batch-report requiere --phase3-batch-dir")
        batch_dir = Path(args.phase3_batch_dir)
        if not batch_dir.exists() or not batch_dir.is_dir():
            parser.error(f"No existe el directorio batch: {batch_dir}")
        files = sorted(batch_dir.glob(args.phase3_batch_glob))
        if not files:
            parser.error(f"No hay archivos para batch con glob: {args.phase3_batch_glob}")
        output_path = write_phase3_batch_report(files, args.phase3_batch_report, pretty=args.pretty)
        print(f"Phase3 batch report escrito: {output_path}")
        return 0

    if not args.input_pcc:
        parser.print_help()
        return 0

    input_path = Path(args.input_pcc)
    if not input_path.exists():
        parser.error(f"No existe el archivo PCC: {input_path}")

    try:
        package = read_pcc(input_path)
    except PccFormatError as exc:
        parser.exit(status=2, message=f"Error leyendo PCC: {exc}\n")

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
        conversations = package.parse_bioconversation_stubs()
        if args.pretty:
            print(json.dumps(conversations, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(conversations, ensure_ascii=False))

    if args.dump_bioconversation_row_payloads:
        payloads = package.inspect_bioconversation_row_payloads()
        if args.pretty:
            print(json.dumps(payloads, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(payloads, ensure_ascii=False))

    if args.phase3_report:
        output_path = write_phase3_report(input_path, args.phase3_report, pretty=args.pretty)
        print(f"Phase3 report escrito: {output_path}")

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
        parser.error("--strict-validation requiere --validate-bioconversation-stubs")
    return 0
