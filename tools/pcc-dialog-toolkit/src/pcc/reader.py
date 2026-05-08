from __future__ import annotations

import struct
from pathlib import Path

from .models import ExportEntry, ImportEntry, NameEntry, PccHeader, PccPackage


class PccFormatError(ValueError):
    pass


ME_PACKAGE_MAGIC = 0x9E2A83C1
COMPRESSED_FLAG = 0x02000000
COMPRESSION_LZO = 0x2
CHUNK_HEADER_MAGIC = 0x9E2A83C1
CHUNK_HEADER_SIZE = 16
CHUNK_BLOCK_HEADER_SIZE = 8


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


def _require_lzo() -> "type":
    try:
        from lzallright import LZOCompressor
    except ImportError as exc:
        raise PccFormatError(
            "Dependencia faltante para LZO: instala 'lzallright' (pip install lzallright)"
        ) from exc
    return LZOCompressor


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

    flags = _read_u32(data, cursor)
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
        flags=flags,
        name_count=name_count,
        name_offset=name_offset,
        export_count=export_count,
        export_offset=export_offset,
        import_count=import_count,
        import_offset=import_offset,
    )


def _locate_compression_info_offset_me2_ot(data: bytes) -> int:
    cursor = 8
    _read_i32(data, cursor)
    cursor += 4

    folder_len = _read_i32(data, cursor)
    cursor += 4
    if folder_len > 0:
        cursor += folder_len
    elif folder_len < 0:
        cursor += (-folder_len) * 2

    _read_u32(data, cursor)
    cursor += 4

    cursor += 4  # name_count
    cursor += 4  # name_offset
    cursor += 4  # export_count
    cursor += 4  # export_offset
    cursor += 4  # import_count
    cursor += 4  # import_offset

    cursor += 4  # dependency_table_offset

    cursor += 16  # package guid

    generations = _read_u32(data, cursor)
    cursor += 4
    if generations > 0:
        cursor += 12
        cursor += (generations - 1) * 12

    cursor += 8  # engine_version, cooked_content_version

    cursor += 16  # me2 pc extra header block

    cursor += 4  # build
    cursor += 4  # branch

    return cursor


def _decompress_me2_ot(data: bytes) -> bytes:
    cursor = _locate_compression_info_offset_me2_ot(data)
    compression_type = _read_i32(data, cursor)
    num_chunks = _read_i32(data, cursor + 4)
    cursor += 8

    if compression_type != COMPRESSION_LZO:
        raise PccFormatError(f"Tipo de compresion no soportado: {compression_type}")
    if num_chunks <= 0:
        raise PccFormatError("Tabla de chunks comprimidos vacia o invalida")

    chunks: list[dict[str, int]] = []
    for _ in range(num_chunks):
        uncompressed_offset = _read_i32(data, cursor)
        uncompressed_size = _read_i32(data, cursor + 4)
        compressed_offset = _read_i32(data, cursor + 8)
        compressed_size = _read_i32(data, cursor + 12)
        chunks.append(
            {
                "uncompressed_offset": uncompressed_offset,
                "uncompressed_size": uncompressed_size,
                "compressed_offset": compressed_offset,
                "compressed_size": compressed_size,
            }
        )
        cursor += 16

    first_chunk_offset = min(item["uncompressed_offset"] for item in chunks)
    max_end = max(item["uncompressed_offset"] + item["uncompressed_size"] for item in chunks)
    if first_chunk_offset < 0 or max_end <= 0:
        raise PccFormatError("Offsets de chunk invalidos")
    if first_chunk_offset > len(data):
        raise PccFormatError("Header truncado antes de datos comprimidos")

    output = bytearray(max_end)
    output[:first_chunk_offset] = data[:first_chunk_offset]

    LZOCompressor = _require_lzo()

    for chunk in chunks:
        compressed_offset = chunk["compressed_offset"]
        compressed_size = chunk["compressed_size"]
        if compressed_offset < 0 or compressed_offset + compressed_size > len(data):
            raise PccFormatError("Chunk comprimido fuera de rango")

        magic = _read_u32(data, compressed_offset)
        block_size = _read_i32(data, compressed_offset + 4)
        compressed_size_header = _read_i32(data, compressed_offset + 8)
        uncompressed_size_header = _read_i32(data, compressed_offset + 12)

        if magic != CHUNK_HEADER_MAGIC:
            raise PccFormatError("Chunk magic invalido")
        if uncompressed_size_header != chunk["uncompressed_size"]:
            raise PccFormatError("Chunk size no coincide con la tabla")
        if compressed_size_header + CHUNK_HEADER_SIZE > compressed_size:
            raise PccFormatError("Chunk header truncado")
        if block_size <= 0:
            raise PccFormatError("Block size invalido en chunk")

        block_count = uncompressed_size_header // block_size
        if uncompressed_size_header % block_size != 0:
            block_count += 1

        block_table_offset = compressed_offset + CHUNK_HEADER_SIZE
        block_data_offset = block_table_offset + (block_count * CHUNK_BLOCK_HEADER_SIZE)
        block_cursor = block_table_offset

        write_offset = chunk["uncompressed_offset"]
        data_cursor = block_data_offset

        for _ in range(block_count):
            block_compressed_size = _read_i32(data, block_cursor)
            block_uncompressed_size = _read_i32(data, block_cursor + 4)
            block_cursor += CHUNK_BLOCK_HEADER_SIZE

            if block_compressed_size < 0 or block_uncompressed_size < 0:
                raise PccFormatError("Block size invalido en chunk")
            if data_cursor + block_compressed_size > compressed_offset + compressed_size:
                raise PccFormatError("Block comprimido fuera de rango")

            block_data = data[data_cursor : data_cursor + block_compressed_size]
            data_cursor += block_compressed_size

            try:
                decompressed = LZOCompressor.decompress(
                    block_data, output_size_hint=block_uncompressed_size
                )
            except Exception as exc:
                raise PccFormatError("Fallo la descompresion LZO") from exc

            if len(decompressed) != block_uncompressed_size:
                raise PccFormatError("Tamano descomprimido no coincide")

            end_offset = write_offset + block_uncompressed_size
            if end_offset > len(output):
                raise PccFormatError("Buffer descomprimido fuera de rango")
            output[write_offset:end_offset] = decompressed
            write_offset = end_offset

    return bytes(output)


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

    if header.flags & COMPRESSED_FLAG:
        if header.unreal_version == 512 and header.licensee_version == 130:
            data = _decompress_me2_ot(data)
            header = _parse_header(data)
            header.flags &= ~COMPRESSED_FLAG
        else:
            raise PccFormatError("Paquete comprimido no soportado para este perfil")
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
