from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PccHeader:
    magic: int
    unreal_version: int
    licensee_version: int
    flags: int
    name_count: int
    name_offset: int
    export_count: int
    export_offset: int
    import_count: int
    import_offset: int


@dataclass(slots=True)
class NameEntry:
    index: int
    text: str


@dataclass(slots=True)
class ImportEntry:
    index: int
    class_package_name_index: int
    class_name_index: int
    package_ref: int
    object_name_index: int


@dataclass(slots=True)
class ExportEntry:
    index: int
    class_index: int
    super_index: int
    package_ref: int
    object_name_index: int
    serial_size: int
    serial_offset: int
    class_name: str | None = None
    object_name: str | None = None


@dataclass(slots=True)
class PccPackage:
    raw_data: bytes
    path: str
    header: PccHeader
    names: list[NameEntry]
    imports: list[ImportEntry]
    exports: list[ExportEntry]

    def infer_game_profile(self) -> str:
        uv = self.header.unreal_version
        lv = self.header.licensee_version
        if uv == 512 and lv == 130:
            return "me2_ot"
        if uv == 684 and lv == 168:
            return "le2"
        if uv == 684 and lv == 194:
            return "me3_ot"
        if uv == 685 and lv == 205:
            return "le3"
        return "unknown"

    def iter_exports(self, *, class_name: str | None = None, object_name: str | None = None) -> list[ExportEntry]:
        results: list[ExportEntry] = []
        for item in self.exports:
            if class_name is not None and item.class_name != class_name:
                continue
            if object_name is not None and item.object_name != object_name:
                continue
            results.append(item)
        return results

    def list_bioconversations(self) -> list[dict[str, int | str | None]]:
        rows: list[dict[str, int | str | None]] = []
        for item in self.iter_exports(class_name="BioConversation"):
            rows.append(
                {
                    "name": item.object_name,
                    "index": item.index,
                    "class": item.class_name,
                    "offset": item.serial_offset,
                    "size": item.serial_size,
                }
            )
        return rows

    def resolve_object_ref(self, ref: int) -> dict[str, int | str | None]:
        if ref == 0:
            return {"ref": ref, "kind": "none", "index": None, "name": None, "class": None}
        if ref > 0:
            idx = ref - 1
            if 0 <= idx < len(self.exports):
                exp = self.exports[idx]
                return {
                    "ref": ref,
                    "kind": "export",
                    "index": exp.index,
                    "name": exp.object_name,
                    "class": exp.class_name,
                }
            return {"ref": ref, "kind": "export", "index": idx, "name": None, "class": None}

        idx = (-ref) - 1
        if 0 <= idx < len(self.imports):
            imp = self.imports[idx]
            name = self.names[imp.object_name_index].text if 0 <= imp.object_name_index < len(self.names) else None
            class_name = self.names[imp.class_name_index].text if 0 <= imp.class_name_index < len(self.names) else None
            return {
                "ref": ref,
                "kind": "import",
                "index": imp.index,
                "name": name,
                "class": class_name,
            }
        return {"ref": ref, "kind": "import", "index": idx, "name": None, "class": None}

    def inspect_bioconversation_owners(self) -> list[dict[str, object]]:
        from .properties import extract_bioconversation_property_tags
        from .reader import _read_i32

        rows: list[dict[str, object]] = []
        for item in self.iter_exports(class_name="BioConversation"):
            tags = extract_bioconversation_property_tags(self.raw_data, self.names, item)
            owner_tag = next(
                (
                    tag
                    for tag in tags
                    if tag.prop_type == "ObjectProperty" and "owner" in tag.name.lower()
                ),
                None,
            )

            owner_ref: int | None = None
            owner_resolved: dict[str, int | str | None] | None = None
            if owner_tag is not None and owner_tag.size >= 4:
                owner_ref = _read_i32(self.raw_data, owner_tag.value_offset)
                owner_resolved = self.resolve_object_ref(owner_ref)

            rows.append(
                {
                    "name": item.object_name,
                    "index": item.index,
                    "owner_property": owner_tag.name if owner_tag else None,
                    "owner_ref": owner_ref,
                    "owner": owner_resolved,
                }
            )
        return rows

    def scan_exports_for_i32_values(
        self,
        targets: set[int],
        *,
        class_name_contains: tuple[str, ...] | None = None,
        max_offsets_per_export: int = 6,
    ) -> list[dict[str, object]]:
        import struct

        if not targets:
            return []

        target_bytes = {value: struct.pack("<i", value) for value in targets}
        if not any(blob in self.raw_data for blob in target_bytes.values()):
            return []

        lowered_filters = tuple(item.casefold() for item in class_name_contains or ())
        rows: list[dict[str, object]] = []

        for item in self.exports:
            if item.serial_size <= 0:
                continue

            class_name = item.class_name or ""
            if lowered_filters and not any(token in class_name.casefold() for token in lowered_filters):
                continue

            start = item.serial_offset
            end = item.serial_offset + item.serial_size
            if start < 0 or end > len(self.raw_data) or start >= end:
                continue

            payload = self.raw_data[start:end]
            if not any(blob in payload for blob in target_bytes.values()):
                continue

            local_hits: dict[int, list[int]] = {}
            for value, signature in target_bytes.items():
                search_from = 0
                while search_from < len(payload):
                    found_at = payload.find(signature, search_from)
                    if found_at < 0:
                        break
                    offsets = local_hits.setdefault(value, [])
                    if len(offsets) < max_offsets_per_export:
                        offsets.append(found_at)
                    search_from = found_at + 1

            if not local_hits:
                continue

            rows.append(
                {
                    "export_index": item.index,
                    "export_name": item.object_name,
                    "class_name": item.class_name,
                    "serial_offset": item.serial_offset,
                    "serial_size": item.serial_size,
                    "hits": [
                        {
                            "strref": strref,
                            "offsets": offsets,
                            "count": len(offsets),
                        }
                        for strref, offsets in sorted(local_hits.items())
                    ],
                }
            )

        return rows

    def inspect_bioconversation_properties(self) -> list[dict[str, object]]:
        from .properties import extract_bioconversation_key_properties, read_array_property_count

        rows: list[dict[str, object]] = []
        for item in self.iter_exports(class_name="BioConversation"):
            key_tags = extract_bioconversation_key_properties(self.raw_data, self.names, item)
            rows.append(
                {
                    "name": item.object_name,
                    "index": item.index,
                    "properties": [
                        {
                            "name": tag.name,
                            "type": tag.prop_type,
                            "size": tag.size,
                            "array_index": tag.array_index,
                            "value_offset": tag.value_offset,
                            "array_count": read_array_property_count(self.raw_data, tag)
                            if tag.prop_type == "ArrayProperty"
                            else None,
                        }
                        for tag in key_tags
                    ],
                }
            )
        return rows

    def inspect_bioconversation_property_tags(self) -> list[dict[str, object]]:
        from .properties import extract_bioconversation_property_tags

        rows: list[dict[str, object]] = []
        for item in self.iter_exports(class_name="BioConversation"):
            tags = extract_bioconversation_property_tags(self.raw_data, self.names, item)
            rows.append(
                {
                    "name": item.object_name,
                    "index": item.index,
                    "properties": [
                        {
                            "name": tag.name,
                            "type": tag.prop_type,
                            "size": tag.size,
                            "array_index": tag.array_index,
                            "value_offset": tag.value_offset,
                        }
                        for tag in tags
                    ],
                }
            )
        return rows

    def parse_bioconversation_stubs(self) -> list[dict[str, object]]:
        from dialogue import parse_all_bioconversation_stubs

        return [item.to_dict() for item in parse_all_bioconversation_stubs(self)]

    def inspect_bioconversation_row_payloads(self) -> list[dict[str, object]]:
        from dialogue import inspect_bioconversation_row_payloads

        return inspect_bioconversation_row_payloads(self)

    def validate_bioconversation_stubs(self) -> list[dict[str, object]]:
        from dialogue import validate_all_bioconversation_stubs

        return validate_all_bioconversation_stubs(self)

    def summarize_bioconversation_validation(self) -> dict[str, object]:
        from dialogue import summarize_stub_validation

        return summarize_stub_validation(self.validate_bioconversation_stubs())
