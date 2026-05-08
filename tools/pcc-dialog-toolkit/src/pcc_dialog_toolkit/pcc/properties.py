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


def parse_property_tags(data: bytes, names: list[NameEntry], *, start_offset: int, size: int, strict: bool = True) -> list[PropertyTag]:
    end = start_offset + size
    if end > len(data):
        raise PccFormatError("Export data fuera de rango")

    tags: list[PropertyTag] = []
    cursor = start_offset

    property_type_names = {
        "ArrayProperty",
        "BoolProperty",
        "ByteProperty",
        "ClassProperty",
        "ComponentProperty",
        "DelegateProperty",
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

    def _is_plausible_tag_start(offset: int) -> bool:
        if offset + 8 > end:
            return False

        name_a = _read_i32(data, offset)
        name_b = _read_i32(data, offset + 4)
        name_a_text = names[name_a].text if 0 <= name_a < len(names) else None
        name_b_text = names[name_b].text if 0 <= name_b < len(names) else None
        if name_a_text == "None" or name_b_text == "None":
            return True

        if offset + 16 > end:
            return False
        type_a = _read_i32(data, offset + 8)
        type_b = _read_i32(data, offset + 12)
        type_a_text = names[type_a].text if 0 <= type_a < len(names) else None
        type_b_text = names[type_b].text if 0 <= type_b < len(names) else None
        return (type_a_text in property_type_names) or (type_b_text in property_type_names)

    while cursor + 16 <= end:
        try:
            # FName can be serialized either as [index, number] or [number, index]
            # depending on package/version context. We infer orientation by checking
            # which candidate at type slot maps to a known property type name.
            name_a = _read_i32(data, cursor)
            name_b = _read_i32(data, cursor + 4)
            type_a = _read_i32(data, cursor + 8)
            type_b = _read_i32(data, cursor + 12)

            type_a_name = names[type_a].text if 0 <= type_a < len(names) else None
            type_b_name = names[type_b].text if 0 <= type_b < len(names) else None

            if type_b_name in property_type_names and type_a_name not in property_type_names:
                type_index = type_b
                name_index = name_b
            else:
                type_index = type_a
                name_index = name_a

            name = _resolve_name(name_index, names)
            cursor += 8

            if name == "None":
                break

            if cursor + 16 > end:
                raise PccFormatError("Property tag truncado antes de type/size/index")

            prop_type_index = type_index
            prop_type = _resolve_name(prop_type_index, names)
            cursor += 8

            prop_size = _read_i32(data, cursor)
            array_index = _read_i32(data, cursor + 4)
            cursor += 8

            # Some ME2 OT samples serialize ArrayProperty size/index in swapped
            # order. If the decoded size is clearly invalid but the companion
            # field looks like a byte length, swap them.
            if prop_type == "ArrayProperty" and prop_size < 4 and array_index >= 4:
                prop_size, array_index = array_index, prop_size

            cursor = _skip_tag_meta(data, cursor, prop_type)
            if prop_type == "ArrayProperty":
                # Real-world PCCs may serialize ArrayProperty with or without the
                # additional FName metadata. Choose the variant that keeps the
                # stream aligned with a plausible next tag.
                no_meta_next = cursor + prop_size
                f_name_meta_next = (cursor + 8) + prop_size
                if _is_plausible_tag_start(f_name_meta_next) and not _is_plausible_tag_start(no_meta_next):
                    cursor += 8
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
        except PccFormatError:
            if strict:
                raise
            break

    return tags


def extract_bioconversation_key_properties(data: bytes, names: list[NameEntry], export: ExportEntry) -> list[PropertyTag]:
    key_aliases = {
        "EntryList": "EntryList",
        "m_EntryList": "EntryList",
        "ReplyList": "ReplyList",
        "m_ReplyList": "ReplyList",
        "ReplyListNew": "ReplyList",
        "SpeakerList": "SpeakerList",
        "m_SpeakerList": "SpeakerList",
    }
    key_props = {"EntryList", "ReplyList", "SpeakerList"}
    parse_errors: list[PccFormatError] = []

    for delta in (0, 4):
        if export.serial_size <= delta:
            continue
        try:
            tags = parse_property_tags(
                data,
                names,
                start_offset=export.serial_offset + delta,
                size=export.serial_size - delta,
                strict=False,
            )
            key_tags: list[PropertyTag] = []
            for tag in tags:
                canonical = key_aliases.get(tag.name)
                if canonical is None:
                    continue
                tag.name = canonical
                if tag.name in key_props:
                    key_tags.append(tag)
            if key_tags:
                return key_tags
        except PccFormatError as exc:
            parse_errors.append(exc)

    if parse_errors:
        # Fallback scan inspired by LegendaryExplorer's BioConversation fields:
        # m_StartingList / m_EntryList / m_ReplyList / m_SpeakerList.
        # We do a bounded fuzzy scan to recover key ArrayProperty tags even when
        # top-level linear tag parsing does not stay aligned for real-world OT files.
        return _scan_bioconversation_key_properties_fuzzy(data, names, export)
    return _scan_bioconversation_key_properties_fuzzy(data, names, export)


def _scan_bioconversation_key_properties_fuzzy(
    data: bytes, names: list[NameEntry], export: ExportEntry
) -> list[PropertyTag]:
    name_to_idx = {entry.text: entry.index for entry in names}
    array_property_idx = name_to_idx.get("ArrayProperty")
    if array_property_idx is None:
        return []

    alias_to_canonical = {
        "EntryList": "EntryList",
        "m_EntryList": "EntryList",
        "ReplyList": "ReplyList",
        "m_ReplyList": "ReplyList",
        "ReplyListNew": "ReplyList",
        "SpeakerList": "SpeakerList",
        "m_SpeakerList": "SpeakerList",
    }

    key_name_indices: dict[int, str] = {}
    for alias, canonical in alias_to_canonical.items():
        idx = name_to_idx.get(alias)
        if idx is not None:
            key_name_indices[idx] = canonical

    if not key_name_indices:
        return []

    start = export.serial_offset
    end = export.serial_offset + export.serial_size
    if start < 0 or end > len(data) or start >= end:
        return []

    found: dict[str, PropertyTag] = {}

    def _resolve_pair_index(a: int, b: int, wanted: set[int]) -> int | None:
        if a in wanted and b not in wanted:
            return a
        if b in wanted and a not in wanted:
            return b
        if a in wanted:
            return a
        if b in wanted:
            return b
        return None

    for pos in range(start, max(start, end - 24), 4):
        try:
            name_a = _read_i32(data, pos)
            name_b = _read_i32(data, pos + 4)
            type_a = _read_i32(data, pos + 8)
            type_b = _read_i32(data, pos + 12)
        except PccFormatError:
            continue

        name_idx = _resolve_pair_index(name_a, name_b, set(key_name_indices.keys()))
        if name_idx is None:
            continue

        type_idx = _resolve_pair_index(type_a, type_b, {array_property_idx})
        if type_idx is None:
            continue

        prop_name = key_name_indices[name_idx]
        if prop_name in found:
            continue

        size_pos = pos + 16
        if size_pos + 8 > end:
            continue

        raw_size = _read_i32(data, size_pos)
        raw_array_index = _read_i32(data, size_pos + 4)

        prop_size = raw_size
        array_index = raw_array_index
        if prop_size < 4 and array_index >= 4:
            prop_size, array_index = array_index, prop_size
        if prop_size < 4:
            continue

        candidates = [size_pos + 8, size_pos + 16]
        chosen_value_offset: int | None = None
        for value_offset in candidates:
            if value_offset + prop_size > end:
                continue
            try:
                count = _read_i32(data, value_offset)
            except PccFormatError:
                continue
            # Keep broad bounds; real data can be large but should be non-negative.
            if 0 <= count <= 200000:
                chosen_value_offset = value_offset
                break

        if chosen_value_offset is None:
            continue

        found[prop_name] = PropertyTag(
            name=prop_name,
            prop_type="ArrayProperty",
            size=prop_size,
            array_index=array_index,
            value_offset=chosen_value_offset,
        )

        if len(found) == 3:
            break

    return [found[key] for key in ("EntryList", "ReplyList", "SpeakerList") if key in found]


def extract_bioconversation_property_tags(data: bytes, names: list[NameEntry], export: ExportEntry) -> list[PropertyTag]:
    tags: list[PropertyTag] = []
    for delta in (0, 4):
        if export.serial_size <= delta:
            continue
        candidate = parse_property_tags(
            data,
            names,
            start_offset=export.serial_offset + delta,
            size=export.serial_size - delta,
            strict=False,
        )
        if len(candidate) > len(tags):
            tags = candidate
    return tags


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


def read_array_property_struct_head_i32(data: bytes, tag: PropertyTag, *, head_i32: int) -> list[list[int]]:
    if head_i32 <= 0:
        raise PccFormatError(f"head_i32 invalido: {head_i32}")

    info = analyze_array_property_layout(data, tag)
    if info.count <= 0 or info.bytes_per_item is None:
        return []
    if info.remainder != 0:
        return []

    stride = info.bytes_per_item
    head_size = head_i32 * 4
    if stride < head_size:
        return []

    rows: list[list[int]] = []
    payload_start = tag.value_offset + 4
    for i in range(info.count):
        item_start = payload_start + (i * stride)
        rows.append([_read_i32(data, item_start + (j * 4)) for j in range(head_i32)])
    return rows


def read_array_property_struct_i32_matrix(data: bytes, tag: PropertyTag) -> list[list[int]]:
    info = analyze_array_property_layout(data, tag)
    if info.count <= 0 or info.bytes_per_item is None:
        return []
    if info.remainder != 0:
        return []
    if info.bytes_per_item % 4 != 0:
        return []

    width = info.bytes_per_item // 4
    if width <= 0:
        return []

    rows: list[list[int]] = []
    payload_start = tag.value_offset + 4
    for i in range(info.count):
        item_start = payload_start + (i * info.bytes_per_item)
        rows.append([_read_i32(data, item_start + (j * 4)) for j in range(width)])
    return rows
