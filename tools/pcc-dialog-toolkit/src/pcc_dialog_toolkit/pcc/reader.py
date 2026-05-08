from __future__ import annotations

import struct
from pathlib import Path

from .models import ExportEntry, ImportEntry, NameEntry, PccHeader, PccPackage


class PccFormatError(ValueError):
    pass


ME_PACKAGE_MAGIC = 0x9E2A83C1


def _read_i32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise PccFormatError(f"Offset fuera de rango: {offset}")
    return struct.unpack_from("<i", data, offset)[0]


def _read_u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise PccFormatError(f"Offset fuera de rango: {offset}")
    return struct.unpack_from("<I", data, offset)[0]


def _read_unreal_string(data: bytes, offset: int) -> tuple[str, int]:
    count = _read_i32(data, offset)
    cursor = offset + 4
    if count == 0:
        return "", cursor
    if count > 0:
        end = cursor + count
        if end > len(data):
            raise PccFormatError("String ASCII truncado")
        raw = data[cursor:end]
        if raw.endswith(b"\x00"):
            raw = raw[:-1]
        return raw.decode("latin-1", errors="replace"), end
    char_count = -count
    end = cursor + (char_count * 2)
    if end > len(data):
        raise PccFormatError("String UTF-16 truncado")
    raw = data[cursor:end]
    if raw.endswith(b"\x00\x00"):
        raw = raw[:-2]
    return raw.decode("utf-16-le", errors="replace"), end


def _parse_header(data: bytes) -> PccHeader:
    if len(data) < 44:
        raise PccFormatError("Archivo demasiado pequeno para header PCC")

    magic = _read_u32(data, 0)
    if magic != ME_PACKAGE_MAGIC:
        raise PccFormatError(f"Magic invalido: 0x{magic:08X}")

    version_pack = _read_u32(data, 4)
    unreal_version = version_pack & 0xFFFF
    licensee_version = (version_pack >> 16) & 0xFFFF

    cursor = 8
    _full_header_size = _read_i32(data, cursor)
    cursor += 4

    folder_len = _read_i32(data, cursor)
    cursor += 4
    if folder_len > 0:
        cursor += folder_len
    elif folder_len < 0:
        cursor += (-folder_len) * 2

    if cursor < 0 or cursor + 4 > len(data):
        raise PccFormatError("Header truncado en package folder")

    _flags = _read_u32(data, cursor)
    cursor += 4

    name_count = _read_i32(data, cursor)
    cursor += 4
    name_offset = _read_i32(data, cursor)
    cursor += 4
    export_count = _read_i32(data, cursor)
    cursor += 4
    export_offset = _read_i32(data, cursor)
    cursor += 4
    import_count = _read_i32(data, cursor)
    cursor += 4
    import_offset = _read_i32(data, cursor)

    if min(name_count, export_count, import_count) < 0:
        raise PccFormatError("Conteos negativos en tablas")

    return PccHeader(
        magic=magic,
        unreal_version=unreal_version,
        licensee_version=licensee_version,
        name_count=name_count,
        name_offset=name_offset,
        export_count=export_count,
        export_offset=export_offset,
        import_count=import_count,
        import_offset=import_offset,
    )


def _parse_names(data: bytes, header: PccHeader) -> list[NameEntry]:
    names: list[NameEntry] = []
    cursor = header.name_offset
    for i in range(header.name_count):
        text, cursor = _read_unreal_string(data, cursor)
        cursor += 8 if header.unreal_version <= 491 else 4
        if cursor > len(data):
            raise PccFormatError("Name table fuera de rango")
        names.append(NameEntry(index=i, text=text))
    return names


def _parse_imports(data: bytes, header: PccHeader) -> list[ImportEntry]:
    imports: list[ImportEntry] = []
    cursor = header.import_offset
    for i in range(header.import_count):
        if cursor + 28 > len(data):
            raise PccFormatError("Import table truncada")
        class_package_name_index = _read_i32(data, cursor)
        class_name_index = _read_i32(data, cursor + 8)
        package_ref = _read_i32(data, cursor + 16)
        object_name_index = _read_i32(data, cursor + 20)
        imports.append(
            ImportEntry(
                index=i,
                class_package_name_index=class_package_name_index,
                class_name_index=class_name_index,
                package_ref=package_ref,
                object_name_index=object_name_index,
            )
        )
        cursor += 28
    return imports


def _parse_exports(data: bytes, header: PccHeader) -> list[ExportEntry]:
    exports: list[ExportEntry] = []
    cursor = header.export_offset
    for i in range(header.export_count):
        if cursor + 44 > len(data):
            raise PccFormatError("Export table truncada")
        class_index = _read_i32(data, cursor)
        super_index = _read_i32(data, cursor + 4)
        package_ref = _read_i32(data, cursor + 8)
        object_name_index = _read_i32(data, cursor + 12)
        serial_size = _read_i32(data, cursor + 32)
        serial_offset = _read_i32(data, cursor + 36)
        exports.append(
            ExportEntry(
                index=i,
                class_index=class_index,
                super_index=super_index,
                package_ref=package_ref,
                object_name_index=object_name_index,
                serial_size=serial_size,
                serial_offset=serial_offset,
            )
        )
        cursor += 68
    return exports


def _resolve_name(name_index: int, names: list[NameEntry]) -> str | None:
    if name_index < 0 or name_index >= len(names):
        return None
    return names[name_index].text


def _resolve_export_class_name(exp: ExportEntry, exports: list[ExportEntry], imports: list[ImportEntry], names: list[NameEntry]) -> str | None:
    if exp.class_index > 0:
        idx = exp.class_index - 1
        if 0 <= idx < len(exports):
            return _resolve_name(exports[idx].object_name_index, names)
        return None
    if exp.class_index < 0:
        idx = (-exp.class_index) - 1
        if 0 <= idx < len(imports):
            return _resolve_name(imports[idx].object_name_index, names)
    return None


def read_pcc(path: str | Path) -> PccPackage:
    p = Path(path)
    data = p.read_bytes()
    header = _parse_header(data)
    names = _parse_names(data, header)
    imports = _parse_imports(data, header)
    exports = _parse_exports(data, header)

    for exp in exports:
        exp.object_name = _resolve_name(exp.object_name_index, names)
        exp.class_name = _resolve_export_class_name(exp, exports, imports, names)

    return PccPackage(
        raw_data=data,
        path=str(p),
        header=header,
        names=names,
        imports=imports,
        exports=exports,
    )
