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
    path: str
    header: PccHeader
    names: list[NameEntry]
    imports: list[ImportEntry]
    exports: list[ExportEntry]

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
