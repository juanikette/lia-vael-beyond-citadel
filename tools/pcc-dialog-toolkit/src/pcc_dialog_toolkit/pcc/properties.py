from __future__ import annotations

from dataclasses import dataclass

from .models import ExportEntry, NameEntry
from .reader import PccFormatError, _read_i32


@dataclass(slots=True)
class PropertyTag:
    name: str
    prop_type: str
    size: int
    array_index: int
    value_offset: int


@dataclass(slots=True)
class ArrayLayoutInfo:
    count: int
    payload_size: int
    bytes_per_item: int | None
    remainder: int
    is_tight_i32: bool


def _resolve_name(name_index: int, names: list[NameEntry]) -> str:
    if 0 <= name_index < len(names):
        return names[name_index].text
    raise PccFormatError(f"Name index invalido en property tag: {name_index}")


def _skip_tag_meta(data: bytes, cursor: int, prop_type: str) -> int:
    if prop_type == "StructProperty":
        return cursor + 8
    if prop_type == "ByteProperty":
        return cursor + 8
    if prop_type == "BoolProperty":
        return cursor + 1
    if prop_type == "ArrayProperty":
        return cursor + 8
    return cursor


def parse_property_tags(data: bytes, names: list[NameEntry], *, start_offset: int, size: int) -> list[PropertyTag]:
    end = start_offset + size
    if end > len(data):
        raise PccFormatError("Export data fuera de rango")

    tags: list[PropertyTag] = []
    cursor = start_offset

    while cursor + 8 <= end:
        name_index = _read_i32(data, cursor)
        name = _resolve_name(name_index, names)
        cursor += 8

        if name == "None":
            break

        if cursor + 16 > end:
            raise PccFormatError("Property tag truncado antes de type/size/index")

        prop_type_index = _read_i32(data, cursor)
        prop_type = _resolve_name(prop_type_index, names)
        cursor += 8

        prop_size = _read_i32(data, cursor)
        array_index = _read_i32(data, cursor + 4)
        cursor += 8

        cursor = _skip_tag_meta(data, cursor, prop_type)
        if cursor > end:
            raise PccFormatError("Property tag fuera de rango en metadata adicional")

        value_offset = cursor
        cursor += prop_size
        if cursor > end:
            raise PccFormatError("Property value fuera de rango")

        tags.append(
            PropertyTag(
                name=name,
                prop_type=prop_type,
                size=prop_size,
                array_index=array_index,
                value_offset=value_offset,
            )
        )

    return tags


def extract_bioconversation_key_properties(data: bytes, names: list[NameEntry], export: ExportEntry) -> list[PropertyTag]:
    key_props = {"EntryList", "ReplyList", "SpeakerList"}
    tags = parse_property_tags(data, names, start_offset=export.serial_offset, size=export.serial_size)
    return [tag for tag in tags if tag.name in key_props]


def read_array_property_count(data: bytes, tag: PropertyTag) -> int:
    if tag.prop_type != "ArrayProperty":
        raise PccFormatError(f"Propiedad no es ArrayProperty: {tag.name}")
    if tag.size < 4:
        raise PccFormatError(f"ArrayProperty sin longitud valida: {tag.name}")
    return _read_i32(data, tag.value_offset)


def read_array_property_i32_values(data: bytes, tag: PropertyTag) -> list[int]:
    count = read_array_property_count(data, tag)
    payload_start = tag.value_offset + 4
    payload_size = tag.size - 4
    expected_size = count * 4

    if count < 0:
        raise PccFormatError(f"ArrayProperty con longitud negativa: {tag.name}")
    # Strict mode: only accept tightly packed i32 arrays.
    # If payload contains extra data, it likely represents struct/object rows
    # and should be handled by a dedicated parser.
    if payload_size != expected_size:
        return []

    values: list[int] = []
    cursor = payload_start
    for _ in range(count):
        values.append(_read_i32(data, cursor))
        cursor += 4
    return values


def read_array_property_i32_rows(data: bytes, tag: PropertyTag, *, item_width: int) -> list[list[int]]:
    if item_width <= 0:
        raise PccFormatError(f"item_width invalido para array: {item_width}")

    values = read_array_property_i32_values(data, tag)
    expected = len(values)
    if expected % item_width != 0:
        return []

    rows: list[list[int]] = []
    cursor = 0
    while cursor < expected:
        rows.append(values[cursor : cursor + item_width])
        cursor += item_width
    return rows


def analyze_array_property_layout(data: bytes, tag: PropertyTag) -> ArrayLayoutInfo:
    count = read_array_property_count(data, tag)
    payload_size = max(0, tag.size - 4)

    if count <= 0:
        return ArrayLayoutInfo(
            count=max(0, count),
            payload_size=payload_size,
            bytes_per_item=None,
            remainder=payload_size,
            is_tight_i32=(payload_size == 0),
        )

    bytes_per_item = payload_size // count
    remainder = payload_size % count
    return ArrayLayoutInfo(
        count=count,
        payload_size=payload_size,
        bytes_per_item=bytes_per_item,
        remainder=remainder,
        is_tight_i32=(remainder == 0 and bytes_per_item == 4),
    )
