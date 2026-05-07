from __future__ import annotations

import argparse
from pathlib import Path

from pcc_dialog_toolkit.pcc import PccFormatError, read_pcc


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
    parser.add_argument("--version", action="store_true", help="Muestra la version actual")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("pcc-dialog-toolkit 0.1.0")
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
    return 0
