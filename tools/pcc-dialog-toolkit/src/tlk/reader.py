from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path


TLK_MAGIC = 0x006B6C54  # "Tlk " in little-endian


class TlkFormatError(ValueError):
    pass


@dataclass(slots=True)
class TlkHeader:
    magic: int
    version: int
    min_version: int
    male_entry_count: int
    female_entry_count: int
    tree_node_count: int
    data_len: int


@dataclass(slots=True)
class TlkNode:
    left_node_id: int
    right_node_id: int


@dataclass(slots=True)
class TlkFile:
    path: str
    header: TlkHeader
    male_stringrefs: dict[int, int]
    female_stringrefs: dict[int, int]
    nodes: list[TlkNode]
    bits: bytes


def _read_i32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise TlkFormatError(f"Offset fuera de rango: {offset}")
    return struct.unpack_from("<i", data, offset)[0]


def _get_bit(data: bytes, index: int) -> bool:
    byte_index = index >> 3
    bit_index = index & 7
    if byte_index < 0 or byte_index >= len(data):
        return False
    return (data[byte_index] & (1 << bit_index)) != 0


def _decode_string_from_bit_offset(bits: bytes, nodes: list[TlkNode], bit_offset: int) -> str | None:
    if bit_offset < 0:
        return None
    if not nodes:
        return None

    root = nodes[0]
    current = root
    chars: list[str] = []
    bits_length = len(bits) * 8

    i = bit_offset
    while i < bits_length:
        next_node_id = current.right_node_id if _get_bit(bits, i) else current.left_node_id
        i += 1
        if next_node_id >= 0:
            if next_node_id >= len(nodes):
                return None
            current = nodes[next_node_id]
            continue

        char_code = (0xFFFF - next_node_id) & 0xFFFF
        c = chr(char_code)
        if c == "\x00":
            return "".join(chars)
        chars.append(c)
        current = root

    return None


def read_tlk(path: str | Path) -> TlkFile:
    tlk_path = Path(path)
    data = tlk_path.read_bytes()
    if len(data) < 28:
        raise TlkFormatError("Archivo TLK demasiado pequeno")

    header = TlkHeader(
        magic=_read_i32(data, 0),
        version=_read_i32(data, 4),
        min_version=_read_i32(data, 8),
        male_entry_count=_read_i32(data, 12),
        female_entry_count=_read_i32(data, 16),
        tree_node_count=_read_i32(data, 20),
        data_len=_read_i32(data, 24),
    )
    if header.magic != TLK_MAGIC:
        raise TlkFormatError(f"Magic TLK invalido: 0x{header.magic:08X}")
    if min(header.male_entry_count, header.female_entry_count, header.tree_node_count, header.data_len) < 0:
        raise TlkFormatError("Header TLK invalido: conteos negativos")

    offset = 28
    male_stringrefs: dict[int, int] = {}
    for _ in range(header.male_entry_count):
        string_id = _read_i32(data, offset)
        bit_offset = _read_i32(data, offset + 4)
        male_stringrefs[string_id] = bit_offset
        offset += 8

    female_stringrefs: dict[int, int] = {}
    for _ in range(header.female_entry_count):
        string_id = _read_i32(data, offset)
        bit_offset = _read_i32(data, offset + 4)
        female_stringrefs[string_id] = bit_offset
        offset += 8

    nodes: list[TlkNode] = []
    for _ in range(header.tree_node_count):
        left_node_id = _read_i32(data, offset)
        right_node_id = _read_i32(data, offset + 4)
        nodes.append(TlkNode(left_node_id=left_node_id, right_node_id=right_node_id))
        offset += 8

    if offset + header.data_len > len(data):
        raise TlkFormatError("Payload Huffman TLK truncado")
    bits = data[offset : offset + header.data_len]

    return TlkFile(
        path=str(tlk_path),
        header=header,
        male_stringrefs=male_stringrefs,
        female_stringrefs=female_stringrefs,
        nodes=nodes,
        bits=bits,
    )


def resolve_tlk_string(tlk: TlkFile, string_id: int, *, male: bool = True) -> str | None:
    lookup = tlk.male_stringrefs if male else tlk.female_stringrefs
    bit_offset = lookup.get(string_id)
    if bit_offset is None or bit_offset < 0:
        return None
    return _decode_string_from_bit_offset(tlk.bits, tlk.nodes, bit_offset)
