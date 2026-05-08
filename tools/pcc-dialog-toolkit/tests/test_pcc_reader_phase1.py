from __future__ import annotations

import struct
from pathlib import Path

import pytest

from pcc import PccFormatError, read_pcc


def _u_string(value: str) -> bytes:
    raw = value.encode("latin-1") + b"\x00"
    return struct.pack("<i", len(raw)) + raw


def _build_minimal_pcc(*, unreal_version: int, licensee_version: int) -> bytes:
    names = ["Core", "Class", "BioConversation", "Conv_Test"]
    name_table = b"".join(_u_string(name) + struct.pack("<i", 0) for name in names)

    # import: class package/name and object name -> BioConversation
    import_entry = struct.pack(
        "<iiiiiii",
        0,
        0,
        1,
        0,
        0,
        2,
        0,
    )

    # export (68 bytes), class_index = -1 (first import), object_name_index = Conv_Test
    export_header = bytearray(68)
    struct.pack_into("<i", export_header, 0, -1)
    struct.pack_into("<i", export_header, 4, 0)
    struct.pack_into("<i", export_header, 8, 0)
    struct.pack_into("<i", export_header, 12, 3)
    struct.pack_into("<i", export_header, 16, 0)
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


@pytest.mark.parametrize(
    ("unreal_version", "licensee_version"),
    [(512, 130), (684, 168)],
)
def test_phase1_reads_names_imports_exports(tmp_path: Path, unreal_version: int, licensee_version: int) -> None:
    pcc_path = tmp_path / "sample.pcc"
    pcc_path.write_bytes(_build_minimal_pcc(unreal_version=unreal_version, licensee_version=licensee_version))

    package = read_pcc(pcc_path)
    assert package.header.unreal_version == unreal_version
    assert package.header.licensee_version == licensee_version
    assert len(package.names) == 4
    assert len(package.imports) == 1
    assert len(package.exports) == 1

    export = package.exports[0]
    assert export.class_name == "BioConversation"
    assert export.object_name == "Conv_Test"
    assert len(package.iter_exports(class_name="BioConversation")) == 1


def test_phase1_invalid_magic_raises_format_error(tmp_path: Path) -> None:
    pcc_path = tmp_path / "bad.pcc"
    pcc_path.write_bytes(b"BAD!" + b"\x00" * 128)

    with pytest.raises(PccFormatError):
        read_pcc(pcc_path)
