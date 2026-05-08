from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

from pcc import read_pcc
from tlk import (
    build_tlk_resolver,
    find_dlc_tlk_files,
    read_tlk,
    resolve_tlk_string,
)


def _u_string(value: str) -> bytes:
    raw = value.encode("latin-1") + b"\x00"
    return struct.pack("<i", len(raw)) + raw


def _prop_tag(name_idx: int, type_idx: int, size: int, array_index: int = 0) -> bytes:
    return struct.pack("<iiiiii", name_idx, 0, type_idx, 0, size, array_index)


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


def _encode_bits(bit_values: list[int]) -> bytes:
    byte_count = (len(bit_values) + 7) // 8
    out = bytearray(byte_count)
    for i, bit in enumerate(bit_values):
        if bit:
            out[i >> 3] |= 1 << (i & 7)
    return bytes(out)


def _build_tlk(entries: dict[int, str]) -> bytes:
    # Huffman tree:
    # node0: left='A', right=node1
    # node1: left='B', right='\0'
    nodes = [(-66, 1), (-67, -1)]
    code_map = {
        "A": [0],
        "B": [1, 0],
        "\x00": [1, 1],
    }

    entry_offsets: dict[int, int] = {}
    bits: list[int] = []
    for string_id, text in entries.items():
        entry_offsets[string_id] = len(bits)
        for c in text:
            bits.extend(code_map[c])
        bits.extend(code_map["\x00"])

    bits_blob = _encode_bits(bits)
    out = bytearray()
    out.extend(struct.pack("<i", 0x006B6C54))
    out.extend(struct.pack("<i", 3))
    out.extend(struct.pack("<i", 2))
    out.extend(struct.pack("<i", len(entries)))
    out.extend(struct.pack("<i", 0))
    out.extend(struct.pack("<i", len(nodes)))
    out.extend(struct.pack("<i", len(bits_blob)))

    for string_id, bit_offset in entry_offsets.items():
        out.extend(struct.pack("<ii", string_id, bit_offset))
    for left, right in nodes:
        out.extend(struct.pack("<ii", left, right))
    out.extend(bits_blob)
    return bytes(out)


def test_tlk_reader_resolves_strings(tmp_path: Path) -> None:
    tlk_path = tmp_path / "BIOGame_INT.tlk"
    tlk_path.write_bytes(_build_tlk({5000: "A", 6000: "B"}))

    tlk = read_tlk(tlk_path)
    assert resolve_tlk_string(tlk, 5000) == "A"
    assert resolve_tlk_string(tlk, 6000) == "B"
    assert resolve_tlk_string(tlk, 9999) is None


def test_tlk_resolver_applies_dlc_override_priority(tmp_path: Path) -> None:
    base_tlk = tmp_path / "BIOGame_INT.tlk"
    base_tlk.write_bytes(_build_tlk({5000: "A", 6000: "B"}))

    dlc_dir = tmp_path / "DLC"
    dlc1 = dlc_dir / "DLC_CON_A" / "CookedPC"
    dlc1.mkdir(parents=True)
    (dlc1.parent / "Mount.dlc").write_text("MountPriority=10\n", encoding="utf-8")
    (dlc1 / "DLC_CON_A_INT.tlk").write_bytes(_build_tlk({5000: "B"}))

    resolver = build_tlk_resolver(base_tlk_path=base_tlk, dlc_dir=dlc_dir)
    assert resolver.resolve(5000) == "B"
    assert resolver.resolve(6000) == "B"


def test_phase4_cli_dump_stub_with_tlk_resolution(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_rows.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads())

    base_tlk = tmp_path / "BIOGame_INT.tlk"
    base_tlk.write_bytes(_build_tlk({5000: "A", 5001: "B", 6000: "A", 6001: "B"}))

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli",
            str(pcc_path),
            "--dump-bioconversation-stub",
            "--tlk",
            str(base_tlk),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = result.stdout.splitlines()[-1]
    rows = json.loads(payload)
    assert rows[0]["entries"][0]["line_strref"] == 5000
    assert rows[0]["entries"][0]["line_text"] == "A"
    assert rows[0]["replies"][1]["line_text"] == "B"


def test_phase4_package_stub_still_available_without_tlk(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_rows_no_tlk.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads())

    package = read_pcc(pcc_path)
    rows = package.parse_bioconversation_stubs()
    assert rows[0]["entries"][0]["line_text"] is None


def test_find_dlc_tlk_files_prefers_mount_priority(tmp_path: Path) -> None:
    dlc_dir = tmp_path / "DLC"

    low = dlc_dir / "DLC_MOD_LOW" / "CookedPC"
    low.mkdir(parents=True)
    (low.parent / "Mount.dlc").write_text("MountPriority=100\n", encoding="utf-8")
    (low / "DLC_MOD_LOW_INT.tlk").write_bytes(_build_tlk({5000: "A"}))

    high = dlc_dir / "DLC_MOD_HIGH" / "CookedPCConsole"
    high.mkdir(parents=True)
    (high.parent / "Mount.dlc").write_text("MountPriority=200\n", encoding="utf-8")
    (high / "DLC_MOD_HIGH_INT.tlk").write_bytes(_build_tlk({5000: "B"}))

    found = find_dlc_tlk_files(dlc_dir)
    assert len(found) == 2
    assert found[0].name == "DLC_MOD_HIGH_INT.tlk"
    assert found[1].name == "DLC_MOD_LOW_INT.tlk"


def test_find_dlc_tlk_files_skips_test_tlks_by_default(tmp_path: Path) -> None:
    dlc_dir = tmp_path / "DLC"
    folder = dlc_dir / "DLC_MOD_ONE" / "CookedPC"
    folder.mkdir(parents=True)
    (folder.parent / "Mount.dlc").write_text("MountPriority=10\n", encoding="utf-8")
    (folder / "DLC_MOD_ONE_INT.tlk").write_bytes(_build_tlk({5000: "A"}))
    (folder / "DLC_MOD_ONE_Test_INT.tlk").write_bytes(_build_tlk({5000: "B"}))

    found_default = find_dlc_tlk_files(dlc_dir)
    found_with_test = find_dlc_tlk_files(dlc_dir, include_test_tlks=True)

    assert [item.name for item in found_default] == ["DLC_MOD_ONE_INT.tlk"]
    assert sorted(item.name for item in found_with_test) == [
        "DLC_MOD_ONE_INT.tlk",
        "DLC_MOD_ONE_Test_INT.tlk",
    ]


def test_find_dlc_tlk_files_falls_back_to_recursive_scan(tmp_path: Path) -> None:
    dlc_dir = tmp_path / "DLC"
    non_dlc = dlc_dir / "RandomFolder" / "CookedPC"
    non_dlc.mkdir(parents=True)
    (non_dlc / "Random_INT.tlk").write_bytes(_build_tlk({5000: "A"}))

    found = find_dlc_tlk_files(dlc_dir)
    assert len(found) == 1
    assert found[0].name == "Random_INT.tlk"
