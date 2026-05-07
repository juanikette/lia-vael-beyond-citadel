from __future__ import annotations

import struct
import json
import subprocess
import sys
from pathlib import Path

from pcc_dialog_toolkit.pcc import read_pcc


def _u_string(value: str) -> bytes:
    raw = value.encode("latin-1") + b"\x00"
    return struct.pack("<i", len(raw)) + raw


def _prop_tag(name_idx: int, type_idx: int, size: int, array_index: int = 0) -> bytes:
    return struct.pack("<iiiiii", name_idx, 0, type_idx, 0, size, array_index)


def _build_pcc_with_bioconv_properties() -> bytes:
    names = [
        "Core",
        "Class",
        "BioConversation",
        "Conv_Test",
        "EntryList",
        "ReplyList",
        "SpeakerList",
        "ArrayProperty",
        "None",
    ]
    name_table = b"".join(_u_string(name) + struct.pack("<i", 0) for name in names)

    import_entry = struct.pack("<iiiiiii", 0, 0, 1, 0, 0, 2, 0)

    prop_blob = bytearray()
    prop_blob.extend(_prop_tag(4, 7, 8))
    prop_blob.extend(struct.pack("<ii", 7, 0))
    prop_blob.extend(b"\x01\x00\x00\x00")
    prop_blob.extend(b"\x0A\x00\x00\x00")
    prop_blob.extend(_prop_tag(5, 7, 12))
    prop_blob.extend(struct.pack("<ii", 7, 0))
    prop_blob.extend(b"\x02\x00\x00\x00")
    prop_blob.extend(b"\x0A\x00\x00\x00")
    prop_blob.extend(b"\xFF\xFF\xFF\xFF")
    prop_blob.extend(_prop_tag(6, 7, 16))
    prop_blob.extend(struct.pack("<ii", 7, 0))
    prop_blob.extend(b"\x03\x00\x00\x00")
    prop_blob.extend(b"\x03\x00\x00\x00")
    prop_blob.extend(b"\x04\x00\x00\x00")
    prop_blob.extend(b"\x05\x00\x00\x00")
    prop_blob.extend(struct.pack("<ii", 8, 0))

    header_size = 64
    name_offset = header_size
    import_offset = name_offset + len(name_table)
    export_offset = import_offset + len(import_entry)
    serial_offset = export_offset + 68

    export_header = bytearray(68)
    struct.pack_into("<i", export_header, 0, -1)
    struct.pack_into("<i", export_header, 4, 0)
    struct.pack_into("<i", export_header, 8, 0)
    struct.pack_into("<i", export_header, 12, 3)
    struct.pack_into("<i", export_header, 32, len(prop_blob))
    struct.pack_into("<i", export_header, 36, serial_offset)

    data = bytearray(header_size)
    struct.pack_into("<I", data, 0, 0x9E2A83C1)
    packed_version = ((130 & 0xFFFF) << 16) | (512 & 0xFFFF)
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
    data.extend(prop_blob)
    return bytes(data)


def test_phase3_stub_ast_counts(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_ast.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_properties())

    package = read_pcc(pcc_path)
    rows = package.parse_bioconversation_stubs()
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "Conv_Test"
    assert len(row["entries"]) == 1
    assert len(row["replies"]) == 2
    assert len(row["speakers"]) == 3
    assert row["entries"][0]["id"] == 10
    assert row["entries"][0]["reply_links"] == [0]
    assert row["replies"][0]["target_entry_id"] == 10
    assert row["replies"][1]["target_entry_id"] is None
    assert [speaker["id"] for speaker in row["speakers"]] == [3, 4, 5]


def test_phase3_cli_dump_stub_json(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_ast.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_properties())

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pcc_dialog_toolkit",
            str(pcc_path),
            "--dump-bioconversation-stub",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = result.stdout.splitlines()[-1]
    rows = json.loads(payload)
    assert len(rows) == 1
    assert rows[0]["id"] == "Conv_Test"
