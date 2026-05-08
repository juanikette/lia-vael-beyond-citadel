from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

from dialogue.conversation_parser import parse_all_bioconversation_stubs_resilient
from pcc import read_pcc
from serialize import build_output_payload, validate_output_payload


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


def test_phase5_output_json_is_versioned(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_rows.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads())
    output_path = tmp_path / "output" / "dialog.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli",
            str(pcc_path),
            "--game",
            "me2",
            "--output",
            str(output_path),
            "--pretty",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "0.1"
    assert payload["input"]["game"] == "me2"
    assert payload["summary"]["conversations_ok"] == 1
    assert payload["summary"]["conversations_failed"] == 0
    assert len(payload["conversations"]) == 1


def test_phase5_resilient_parser_continues_after_error(monkeypatch, tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_rows.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads())
    package = read_pcc(pcc_path)

    from dialogue import conversation_parser as parser_module

    original = parser_module.parse_bioconversation_stub

    def flaky_parse(pkg, export):
        if export.index == 0:
            raise ValueError("forced failure")
        return original(pkg, export)

    monkeypatch.setattr(parser_module, "parse_bioconversation_stub", flaky_parse)
    rows, errors = parse_all_bioconversation_stubs_resilient(package)
    assert len(rows) == 0
    assert len(errors) == 1
    assert errors[0]["export_index"] == 0
    assert "forced failure" in str(errors[0]["error"])


def test_phase5_output_contract_validator_rejects_inconsistent_summary() -> None:
    payload = build_output_payload(
        input_pcc="sample.pcc",
        game="me2",
        conversations=[],
        errors=[],
    )
    payload["summary"]["conversations_total"] = 1
    try:
        validate_output_payload(payload)
    except ValueError as exc:
        assert "inconsistent" in str(exc)
    else:
        raise AssertionError("Expected validate_output_payload to fail")
