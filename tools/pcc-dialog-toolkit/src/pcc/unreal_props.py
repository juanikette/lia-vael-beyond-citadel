from __future__ import annotations

from dataclasses import dataclass

from .models import NameEntry
from .reader import PccFormatError, _read_i32


@dataclass(slots=True)
class ParsedProperty:
    name: str
    prop_type: str
    value: object


PROPERTY_TYPE_NAMES = {
    "ArrayProperty",
    "BoolProperty",
    "ByteProperty",
    "ClassProperty",
    "ComponentProperty",
    "DelegateProperty",
    "EnumProperty",
    "FloatProperty",
    "InterfaceProperty",
    "IntProperty",
    "MapProperty",
    "NameProperty",
    "ObjectProperty",
    "StrProperty",
    "StringRefProperty",
    "StructProperty",
}


def _resolve_name(name_index: int, names: list[NameEntry]) -> str:
    if 0 <= name_index < len(names):
        return names[name_index].text
    raise PccFormatError(f"Invalid name index in property parse: {name_index}")


def _read_fname(data: bytes, names: list[NameEntry], offset: int) -> tuple[str, int]:
    a = _read_i32(data, offset)
    b = _read_i32(data, offset + 4)
    a_name = names[a].text if 0 <= a < len(names) else None
    b_name = names[b].text if 0 <= b < len(names) else None

    # Prefer candidate that looks like a valid property-type slot orientation.
    if b_name in PROPERTY_TYPE_NAMES and a_name not in PROPERTY_TYPE_NAMES:
        return _resolve_name(b, names), 8
    return _resolve_name(a, names), 8


def _is_plausible_property_start(data: bytes, names: list[NameEntry], offset: int, end: int) -> bool:
    if offset + 8 > end:
        return False
    a = _read_i32(data, offset)
    b = _read_i32(data, offset + 4)
    a_name = names[a].text if 0 <= a < len(names) else None
    b_name = names[b].text if 0 <= b < len(names) else None
    if a_name == "None" or b_name == "None":
        return True
    if offset + 16 > end:
        return False
    ta = _read_i32(data, offset + 8)
    tb = _read_i32(data, offset + 12)
    ta_name = names[ta].text if 0 <= ta < len(names) else None
    tb_name = names[tb].text if 0 <= tb < len(names) else None
    return ta_name in PROPERTY_TYPE_NAMES or tb_name in PROPERTY_TYPE_NAMES


def _parse_property_header(
    data: bytes, names: list[NameEntry], cursor: int, end: int
) -> tuple[str, str, int, int, int, int]:
    if cursor + 24 > end:
        raise PccFormatError("Truncated property header")

    name, name_len = _read_fname(data, names, cursor)
    cursor += name_len
    if name == "None":
        return name, "", 0, 0, cursor, cursor

    prop_type, type_len = _read_fname(data, names, cursor)
    cursor += type_len

    prop_size = _read_i32(data, cursor)
    array_index = _read_i32(data, cursor + 4)
    cursor += 8

    # Additional metadata after type/size/index.
    meta_size = 0
    if prop_type in {"StructProperty", "ByteProperty"}:
        meta_size = 8
    elif prop_type == "BoolProperty":
        one_byte_next = cursor + 1 + prop_size
        four_byte_next = cursor + 4 + prop_size
        meta_size = 4 if _is_plausible_property_start(data, names, four_byte_next, end) and not _is_plausible_property_start(
            data, names, one_byte_next, end
        ) else 1
    elif prop_type == "ArrayProperty":
        no_meta_next = cursor + prop_size
        f_name_meta_next = cursor + 8 + prop_size
        if _is_plausible_property_start(data, names, f_name_meta_next, end) and not _is_plausible_property_start(
            data, names, no_meta_next, end
        ):
            meta_size = 8

    if cursor + meta_size > end:
        raise PccFormatError("Truncated property metadata")
    value_offset = cursor + meta_size

    return name, prop_type, prop_size, array_index, value_offset, meta_size


def parse_property_collection(
    data: bytes,
    names: list[NameEntry],
    *,
    start_offset: int,
    max_size: int,
) -> tuple[dict[str, ParsedProperty], int]:
    end = min(len(data), start_offset + max_size)
    cursor = start_offset
    props: dict[str, ParsedProperty] = {}

    while cursor + 8 <= end:
        try:
            name, prop_type, prop_size, _array_index, value_offset, meta_size = _parse_property_header(
                data, names, cursor, end
            )
        except PccFormatError:
            if props:
                return props, cursor
            raise
        if name == "None":
            return props, value_offset

        # move to post-header
        cursor += 16 + 8 + meta_size  # fname + fname + size/index + meta

        if prop_size < 0:
            if props:
                return props, cursor
            raise PccFormatError(f"Invalid property size: {name}")
        if value_offset + prop_size > end:
            if props:
                return props, cursor
            raise PccFormatError(f"Property value out of range: {name}")

        value: object = None
        if prop_type in {"IntProperty", "ObjectProperty", "StringRefProperty", "NameProperty", "EnumProperty"}:
            if prop_size >= 4:
                raw = _read_i32(data, value_offset)
                if prop_type in {"NameProperty", "EnumProperty"} and 0 <= raw < len(names):
                    value = names[raw].text
                else:
                    value = raw
        elif prop_type == "BoolProperty":
            if meta_size >= 4:
                value = _read_i32(data, value_offset - meta_size) != 0
            else:
                value = data[value_offset - 1] != 0
        elif prop_type == "ArrayProperty":
            # Minimal array parse: count + raw payload span.
            count = _read_i32(data, value_offset)
            value = {
                "count": count,
                "payload_offset": value_offset + 4,
                "payload_size": max(0, prop_size - 4),
            }
        elif prop_type == "StructProperty":
            # Parse nested property collection within bounded struct payload.
            nested, _ = parse_property_collection(
                data,
                names,
                start_offset=value_offset,
                max_size=prop_size,
            )
            value = nested

        props[name] = ParsedProperty(name=name, prop_type=prop_type, value=value)
        cursor = value_offset + prop_size

    return props, cursor


def parse_struct_array_items_as_property_collections(
    data: bytes,
    names: list[NameEntry],
    *,
    payload_offset: int,
    payload_size: int,
    count: int,
) -> list[dict[str, ParsedProperty]]:
    if count <= 0 or payload_size <= 0:
        return []

    end = min(len(data), payload_offset + payload_size)
    cursor = payload_offset
    items: list[dict[str, ParsedProperty]] = []

    starts = _find_repeated_struct_item_starts(data, names, payload_offset, end, count)
    if len(starts) > 1:
        bounds = starts + [end]
        for index, item_start in enumerate(starts):
            item_end = bounds[index + 1]
            try:
                item, _ = parse_property_collection(
                    data,
                    names,
                    start_offset=item_start,
                    max_size=item_end - item_start,
                )
            except PccFormatError:
                continue
            items.append(item)
        return items

    if payload_size % count == 0:
        stride = payload_size // count
        if stride > 0:
            for item_index in range(count):
                item_start = payload_offset + (item_index * stride)
                try:
                    item, _ = parse_property_collection(
                        data,
                        names,
                        start_offset=item_start,
                        max_size=stride,
                    )
                except PccFormatError:
                    break
                items.append(item)
            return items

    # Best-effort: each item is a struct-serialized property collection ending at None.
    for _ in range(count):
        if cursor + 8 > end:
            break
        try:
            item, next_cursor = parse_property_collection(
                data,
                names,
                start_offset=cursor,
                max_size=end - cursor,
            )
        except PccFormatError:
            break
        items.append(item)
        if next_cursor <= cursor:
            break
        cursor = next_cursor

    return items


def _find_repeated_struct_item_starts(
    data: bytes, names: list[NameEntry], payload_offset: int, end: int, count: int
) -> list[int]:
    if count <= 1 or payload_offset + 16 > end:
        return []

    first_a = _read_i32(data, payload_offset)
    first_b = _read_i32(data, payload_offset + 4)
    if not _is_plausible_property_start(data, names, payload_offset, end):
        return []

    starts: list[int] = []
    for pos in range(payload_offset, end - 16, 4):
        if _read_i32(data, pos) != first_a or _read_i32(data, pos + 4) != first_b:
            continue
        if not _is_plausible_property_start(data, names, pos, end):
            continue
        starts.append(pos)
        if len(starts) == count:
            break

    return starts if len(starts) > 1 else []
