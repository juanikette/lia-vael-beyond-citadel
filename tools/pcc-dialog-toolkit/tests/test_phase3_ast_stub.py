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


def _build_pcc_with_bioconv_row_payloads() -> bytes:
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

    # EntryList rows: [id, speaker_id, line_strref] -> 2 rows
    entry_values = [100, 1, 5000, 101, 2, 5001]
    # ReplyList rows: [id, target_entry_id, line_strref] -> 2 rows
    reply_values = [200, 100, 6000, 201, 101, 6001]
    # SpeakerList rows: [id, tag_name_index, display_name_strref] -> 2 rows
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


def _build_pcc_with_bioconv_row_payloads_missing_target() -> bytes:
    names = [
        "Core",
        "Class",
        "BioConversation",
        "Conv_RowPayload_MissingTarget",
        "EntryList",
        "ReplyList",
        "SpeakerList",
        "ArrayProperty",
        "None",
        "SPK_Joker",
    ]
    name_table = b"".join(_u_string(name) + struct.pack("<i", 0) for name in names)

    import_entry = struct.pack("<iiiiiii", 0, 0, 1, 0, 0, 2, 0)

    entry_values = [100, 1, 5000]
    reply_values = [200, 999, 6000]
    speaker_values = [1, 9, 7000]

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


def _build_pcc_with_bioconv_struct_items() -> bytes:
    names = [
        "Core",
        "Class",
        "BioConversation",
        "Conv_StructItems",
        "EntryList",
        "ReplyList",
        "SpeakerList",
        "ArrayProperty",
        "None",
        "SPK_Edi",
    ]
    name_table = b"".join(_u_string(name) + struct.pack("<i", 0) for name in names)

    import_entry = struct.pack("<iiiiiii", 0, 0, 1, 0, 0, 2, 0)

    # count = number of items, each item is 16 bytes (4 i32)
    # We read first 3 i32 as bootstrap head for mapping.
    entry_items = [
        [300, 30, 5300, 1111],
        [301, 31, 5301, 1112],
    ]
    reply_items = [
        [400, 300, 6400, 2221],
        [401, 301, 6401, 2222],
    ]
    speaker_items = [
        [30, 9, 7300, 3331],
        [31, 9, 7301, 3332],
    ]

    def _pack_items(items: list[list[int]]) -> bytes:
        blob = bytearray()
        blob.extend(struct.pack("<i", len(items)))
        for item in items:
            for value in item:
                blob.extend(struct.pack("<i", value))
        return bytes(blob)

    entry_blob = _pack_items(entry_items)
    reply_blob = _pack_items(reply_items)
    speaker_blob = _pack_items(speaker_items)

    prop_blob = bytearray()
    prop_blob.extend(_prop_tag(4, 7, len(entry_blob)))
    prop_blob.extend(struct.pack("<ii", 7, 0))
    prop_blob.extend(entry_blob)

    prop_blob.extend(_prop_tag(5, 7, len(reply_blob)))
    prop_blob.extend(struct.pack("<ii", 7, 0))
    prop_blob.extend(reply_blob)

    prop_blob.extend(_prop_tag(6, 7, len(speaker_blob)))
    prop_blob.extend(struct.pack("<ii", 7, 0))
    prop_blob.extend(speaker_blob)

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
    assert row["game_profile"] == "me2_ot"
    assert len(row["entries"]) == 1
    assert len(row["replies"]) == 2
    assert len(row["speakers"]) == 3
    assert row["entries"][0]["id"] == 10
    assert row["entries"][0]["reply_links"] == [0]
    assert row["replies"][0]["target_entry_id"] == 10
    assert row["replies"][1]["target_entry_id"] is None
    assert [speaker["id"] for speaker in row["speakers"]] == [3, 4, 5]
    assert row["parse_mode"] == "count_or_value_fallback"
    assert "partial_row_payload_detected_fallback_applied" in row["warnings"]


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


def test_phase3_stub_ast_row_payload_mapping(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_rows.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads())

    package = read_pcc(pcc_path)
    rows = package.parse_bioconversation_stubs()
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "Conv_RowPayload"
    assert row["game_profile"] == "me2_ot"
    assert [item["id"] for item in row["entries"]] == [100, 101]
    assert [item["speaker_id"] for item in row["entries"]] == [1, 2]
    assert [item["line_strref"] for item in row["entries"]] == [5000, 5001]
    assert [item["id"] for item in row["replies"]] == [200, 201]
    assert [item["target_entry_id"] for item in row["replies"]] == [100, 101]
    assert [item["line_strref"] for item in row["replies"]] == [6000, 6001]
    assert [item["id"] for item in row["speakers"]] == [1, 2]
    assert [item["tag"] for item in row["speakers"]] == ["SPK_Joker", "SPK_Joker"]
    assert row["parse_mode"] == "row_payload"
    assert row["warnings"] == []


def test_phase3_stub_warns_on_missing_target(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_warn.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads_missing_target())

    package = read_pcc(pcc_path)
    row = package.parse_bioconversation_stubs()[0]
    assert row["parse_mode"] == "row_payload"
    assert row["warnings"] == ["reply_target_missing_entry:200->999"]


def test_phase3_unknown_profile_warning(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_unknown_profile.pcc"
    payload = bytearray(_build_pcc_with_bioconv_row_payloads())
    # patch packed version to unknown (unreal=999, licensee=1)
    packed = ((1 & 0xFFFF) << 16) | (999 & 0xFFFF)
    payload[4:8] = struct.pack("<I", packed)
    pcc_path.write_bytes(bytes(payload))

    package = read_pcc(pcc_path)
    row = package.parse_bioconversation_stubs()[0]
    assert row["game_profile"] == "unknown"
    assert "unknown_game_profile" in row["warnings"]


def test_phase3_cli_dump_row_payloads_json(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_rows_cli.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads())

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pcc_dialog_toolkit",
            str(pcc_path),
            "--dump-bioconversation-row-payloads",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = result.stdout.splitlines()[-1]
    rows = json.loads(payload)
    assert len(rows) == 1
    assert rows[0]["id"] == "Conv_RowPayload"
    assert rows[0]["row_payload_complete"] is True
    assert rows[0]["entry_rows"][0] == [100, 1, 5000]
    assert rows[0]["array_layouts"]["EntryList"]["is_tight_i32"] is True


def test_phase3_row_payload_dump_empty_for_non_tight_i32_arrays(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_non_tight.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_properties())

    package = read_pcc(pcc_path)
    rows = package.inspect_bioconversation_row_payloads()
    assert len(rows) == 1
    row = rows[0]
    assert row["row_payload_complete"] is False
    assert row["entry_rows"] == []
    assert row["reply_rows"] == []
    assert row["speaker_rows"] == [[3, 4, 5]]
    assert row["array_layouts"]["EntryList"]["is_tight_i32"] is True


def test_phase3_struct_head_mode_mapping(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_struct_items.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_struct_items())

    package = read_pcc(pcc_path)
    row = package.parse_bioconversation_stubs()[0]
    assert row["parse_mode"] == "row_payload_struct_matrix"
    assert row["warnings"] == []
    assert [entry["id"] for entry in row["entries"]] == [300, 301]
    assert [entry["speaker_id"] for entry in row["entries"]] == [30, 31]
    assert [entry["listener_tag"] for entry in row["entries"]] == [None, None]
    assert [reply["target_entry_id"] for reply in row["replies"]] == [300, 301]
    assert row["replies"][0]["condition_refs"] == ["cond_i32:2221"]
    assert row["replies"][1]["condition_refs"] == ["cond_i32:2222"]
    assert [speaker["tag"] for speaker in row["speakers"]] == ["SPK_Edi", "SPK_Edi"]
    assert [speaker["display_name"] for speaker in row["speakers"]] == ["strref:7300", "strref:7301"]

    dump = package.inspect_bioconversation_row_payloads()[0]
    assert dump["used_struct_matrix"] is True
    assert dump["array_layouts"]["EntryList"]["bytes_per_item"] == 16
