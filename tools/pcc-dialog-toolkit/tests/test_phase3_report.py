from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

lzallright = pytest.importorskip("lzallright")
LZOCompressor = lzallright.LZOCompressor

from pcc_dialog_toolkit.validation import (
    build_phase3_batch_report,
    build_phase3_report,
    write_phase3_report,
)
from tests.test_phase3_ast_stub import _build_pcc_with_bioconv_row_payloads


def _u_string(value: str) -> bytes:
    raw = value.encode("latin-1") + b"\x00"
    return struct.pack("<i", len(raw)) + raw


def _prop_tag(name_idx: int, type_idx: int, size: int, array_index: int = 0) -> bytes:
    return struct.pack("<iiiiii", name_idx, 0, type_idx, 0, size, array_index)


def _build_me2_ot_compressed_row_payloads() -> bytes:
    names = [
        "Core",
        "Class",
        "BioConversation",
        "Conv_RowPayload",
        "EntryList",
        "ReplyList",
        "SpeakerList",
        "ArrayProperty",
        "None",
        "SPK_Joker",
    ]
    name_table = b"".join(_u_string(name) + struct.pack("<i", 0) for name in names)

    import_entry = struct.pack("<iiiiiii", 0, 0, 1, 0, 0, 2, 0)

    entry_values = [100, 1, 5000, 101, 2, 5001]
    reply_values = [200, 100, 6000, 201, 101, 6001]
    speaker_values = [1, 9, 7000, 2, 9, 7001]

    prop_blob = bytearray()
    prop_blob.extend(_prop_tag(4, 7, 4 + len(entry_values) * 4))
    prop_blob.extend(struct.pack("<ii", 7, 0))
    prop_blob.extend(struct.pack("<i", len(entry_values)))
    for value in entry_values:
        prop_blob.extend(struct.pack("<i", value))

    prop_blob.extend(_prop_tag(5, 7, 4 + len(reply_values) * 4))
    prop_blob.extend(struct.pack("<ii", 7, 0))
    prop_blob.extend(struct.pack("<i", len(reply_values)))
    for value in reply_values:
        prop_blob.extend(struct.pack("<i", value))

    prop_blob.extend(_prop_tag(6, 7, 4 + len(speaker_values) * 4))
    prop_blob.extend(struct.pack("<ii", 7, 0))
    prop_blob.extend(struct.pack("<i", len(speaker_values)))
    for value in speaker_values:
        prop_blob.extend(struct.pack("<i", value))

    prop_blob.extend(struct.pack("<ii", 8, 0))

    export_header_size = 68
    import_offset = 0
    export_offset = 0
    serial_offset = 0

    header_size = 148
    name_offset = header_size
    import_offset = name_offset + len(name_table)
    export_offset = import_offset + len(import_entry)
    serial_offset = export_offset + export_header_size

    export_header = bytearray(export_header_size)
    struct.pack_into("<i", export_header, 0, -1)
    struct.pack_into("<i", export_header, 4, 0)
    struct.pack_into("<i", export_header, 8, 0)
    struct.pack_into("<i", export_header, 12, 3)
    struct.pack_into("<i", export_header, 32, len(prop_blob))
    struct.pack_into("<i", export_header, 36, serial_offset)

    uncompressed_body = bytearray()
    uncompressed_body.extend(name_table)
    uncompressed_body.extend(import_entry)
    uncompressed_body.extend(export_header)
    uncompressed_body.extend(prop_blob)

    compressor = LZOCompressor()
    compressed_block = compressor.compress(bytes(uncompressed_body))
    block_table = struct.pack("<ii", len(compressed_block), len(uncompressed_body))

    chunk_header = struct.pack(
        "<Iiii",
        0x9E2A83C1,
        0x20000,
        len(block_table) + len(compressed_block),
        len(uncompressed_body),
    )
    chunk_data = chunk_header + block_table + compressed_block

    chunk_table_offset = 120
    compressed_offset = header_size + 16
    compressed_size = len(chunk_data)

    data = bytearray(header_size)
    struct.pack_into("<I", data, 0, 0x9E2A83C1)
    packed_version = ((130 & 0xFFFF) << 16) | (512 & 0xFFFF)
    struct.pack_into("<I", data, 4, packed_version)
    struct.pack_into("<i", data, 8, header_size)
    struct.pack_into("<i", data, 12, 0)
    struct.pack_into("<I", data, 16, 0x02000000)
    struct.pack_into("<i", data, 20, len(names))
    struct.pack_into("<i", data, 24, name_offset)
    struct.pack_into("<i", data, 28, 1)
    struct.pack_into("<i", data, 32, export_offset)
    struct.pack_into("<i", data, 36, 1)
    struct.pack_into("<i", data, 40, import_offset)
    struct.pack_into("<i", data, 44, export_offset + export_header_size)
    struct.pack_into("<16s", data, 48, b"\x00" * 16)
    struct.pack_into("<I", data, 64, 1)
    struct.pack_into("<i", data, 68, 1)
    struct.pack_into("<i", data, 72, len(names))
    struct.pack_into("<i", data, 76, 0)
    struct.pack_into("<i", data, 80, 0)
    struct.pack_into("<i", data, 84, 0)
    struct.pack_into("<i", data, 88, 0)
    struct.pack_into("<i", data, 92, 47699)
    struct.pack_into("<i", data, 96, 0)
    struct.pack_into("<i", data, 100, 1966080)
    struct.pack_into("<i", data, 104, 0)
    struct.pack_into("<i", data, 108, 0)
    struct.pack_into("<i", data, 112, 2)
    struct.pack_into("<i", data, 116, 1)
    struct.pack_into("<iiii", data, chunk_table_offset, name_offset, len(uncompressed_body), compressed_offset, compressed_size)
    struct.pack_into("<I", data, 136, 0)
    struct.pack_into("<i", data, 140, 0)
    struct.pack_into("<i", data, 144, 0)

    data.extend(b"\x00" * 16)
    data.extend(chunk_data)
    return bytes(data)


def test_phase3_build_report_structure(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_report.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads())

    report = build_phase3_report(pcc_path)
    assert report["game_profile"] == "me2_ot"
    assert "summary" in report
    assert "validation_items" in report
    assert "row_payloads" in report
    assert report["parse_error"] is None


def test_phase3_write_report_file(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_report.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads())
    out = tmp_path / "reports" / "phase3.json"

    written = write_phase3_report(pcc_path, out, pretty=True)
    assert written.exists()
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["summary"]["total"] == 1


def test_phase3_cli_writes_report_file(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_report.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads())
    out = tmp_path / "phase3-cli.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pcc_dialog_toolkit",
            str(pcc_path),
            "--phase3-report",
            str(out),
            "--pretty",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["summary"]["total"] == 1


def test_phase3_build_report_handles_parse_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pcc"
    bad.write_bytes(b"BAD!" + b"\x00" * 16)

    report = build_phase3_report(bad)
    assert report["parse_error"] is not None
    assert report["summary"]["needs_schema_review"] == 1


def test_phase3_build_report_handles_validation_parse_error(tmp_path: Path) -> None:
    pcc_path = tmp_path / "invalid_property_tag.pcc"
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

    export_header_size = 68
    header_size = 64
    name_offset = header_size
    import_offset = name_offset + len(name_table)
    export_offset = import_offset + len(import_entry)
    serial_offset = export_offset + export_header_size

    export_header = bytearray(export_header_size)
    struct.pack_into("<i", export_header, 0, -1)
    struct.pack_into("<i", export_header, 4, 0)
    struct.pack_into("<i", export_header, 8, 0)
    struct.pack_into("<i", export_header, 12, 3)
    struct.pack_into("<i", export_header, 32, 24)
    struct.pack_into("<i", export_header, 36, serial_offset)

    prop_blob = struct.pack("<iiiiii", 9999, 0, 7, 0, 0, 0)

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
    pcc_path.write_bytes(bytes(data))

    report = build_phase3_report(pcc_path)
    assert report["parse_error"] is None
    assert report["summary"]["total"] == 1


def test_phase3_build_report_handles_compressed_flag(tmp_path: Path) -> None:
    pcc_path = tmp_path / "compressed.pcc"
    pcc_path.write_bytes(_build_me2_ot_compressed_row_payloads())

    report = build_phase3_report(pcc_path)
    assert report["parse_error"] is None


def test_phase3_batch_summary_counts_parse_errors(tmp_path: Path) -> None:
    ok = tmp_path / "ok.pcc"
    bad = tmp_path / "bad.pcc"
    ok.write_bytes(_build_pcc_with_bioconv_row_payloads())
    bad.write_bytes(b"BAD!" + b"\x00" * 16)

    batch = build_phase3_batch_report([ok, bad])
    assert batch["summary"]["files"] == 2
    assert batch["summary"]["parse_errors"] == 1
