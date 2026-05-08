from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PccHeader:
    magic: int
    unreal_version: int
    licensee_version: int
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

    def parse_bioconversation_stubs(self) -> list[dict[str, object]]:
        from pcc_dialog_toolkit.dialogue import parse_all_bioconversation_stubs

        return [item.to_dict() for item in parse_all_bioconversation_stubs(self)]

    def inspect_bioconversation_row_payloads(self) -> list[dict[str, object]]:
        from pcc_dialog_toolkit.dialogue import inspect_bioconversation_row_payloads

        return inspect_bioconversation_row_payloads(self)

    def validate_bioconversation_stubs(self) -> list[dict[str, object]]:
        from pcc_dialog_toolkit.dialogue import validate_all_bioconversation_stubs

        return validate_all_bioconversation_stubs(self)

    def summarize_bioconversation_validation(self) -> dict[str, object]:
        from pcc_dialog_toolkit.dialogue import summarize_stub_validation

        return summarize_stub_validation(self.validate_bioconversation_stubs())
