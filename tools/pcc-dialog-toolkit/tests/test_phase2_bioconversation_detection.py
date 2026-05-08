from __future__ import annotations

import subprocess
import struct
import sys
from pathlib import Path

from pcc import read_pcc


def _u_string(value: str) -> bytes:
    raw = value.encode("latin-1") + b"\x00"
    return struct.pack("<i", len(raw)) + raw


def _build_minimal_pcc(*, unreal_version: int, licensee_version: int) -> bytes:
    names = ["Core", "Class", "BioConversation", "Conv_Test"]
    name_table = b"".join(_u_string(name) + struct.pack("<i", 0) for name in names)

    import_entry = struct.pack("<iiiiiii", 0, 0, 1, 0, 0, 2, 0)
    export_header = bytearray(68)
    struct.pack_into("<i", export_header, 0, -1)
    struct.pack_into("<i", export_header, 4, 0)
    struct.pack_into("<i", export_header, 8, 0)
    struct.pack_into("<i", export_header, 12, 3)
    struct.pack_into("<i", export_header, 32, 0)
    struct.pack_into("<i", export_header, 36, 256)

    header_size = 64
    name_offset = header_size
    import_offset = name_offset + len(name_table)
    export_offset = import_offset + len(import_entry)

    data = bytearray(header_size)
    struct.pack_into("<I", data, 0, 0x9E2A83C1)
    packed_version = ((licensee_version & 0xFFFF) << 16) | (unreal_version & 0xFFFF)
    struct.pack_into("<I", data, 4, packed_version)
    struct.pack_into("<i", data, 20, len(names))
    struct.pack_into("<i", data, 24, name_offset)
    struct.pack_into("<i", data, 28, 1)
    struct.pack_into("<i", data, 32, export_offset)
    struct.pack_into("<i", data, 36, 1)
    struct.pack_into("<i", data, 40, import_offset)

    data.extend(name_table)
    data.extend(import_entry)
    data.extend(export_header)
    return bytes(data)


def test_phase2_bioconversation_metadata_dump(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample.pcc"
    pcc_path.write_bytes(_build_minimal_pcc(unreal_version=512, licensee_version=130))

    package = read_pcc(pcc_path)
    rows = package.list_bioconversations()
    assert len(rows) == 1
    assert rows[0]["name"] == "Conv_Test"
    assert rows[0]["class"] == "BioConversation"
    assert rows[0]["offset"] == 256
    assert rows[0]["size"] == 0


def test_phase2_cli_lists_bioconversations(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample.pcc"
    pcc_path.write_bytes(_build_minimal_pcc(unreal_version=684, licensee_version=168))

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli",
            str(pcc_path),
            "--list-bioconversations",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "BioConversation exports: 1" in result.stdout
    assert "name=Conv_Test" in result.stdout
