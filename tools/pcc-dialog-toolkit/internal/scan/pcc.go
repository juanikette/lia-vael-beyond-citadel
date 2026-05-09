package scan

import (
	"encoding/binary"
	"errors"
	"unicode/utf16"

	lzo "github.com/anchore/go-lzo"
)

const mePackageMagic = 0x9E2A83C1
const compressedFlag = 0x02000000
const compressionLZO = 0x2
const chunkHeaderMagic = 0x9E2A83C1
const chunkHeaderSize = 16
const chunkBlockHeaderSize = 8

type pccHeader struct {
	UnrealVersion   int
	LicenseeVersion int
	Flags           uint32
	NameCount       int
	NameOffset      int
	ExportCount     int
	ExportOffset    int
	ImportCount     int
	ImportOffset    int
}

type pccImport struct {
	ClassNameIndex  int
	ObjectNameIndex int
}

type pccExport struct {
	Index           int
	ClassIndex      int
	ObjectNameIndex int
	SerialSize      int
	SerialOffset    int
	ObjectName      string
	ClassName       string
}

func mapOffsetsToContainers(data []byte, offsets map[int][]int) ([]ContainerHit, string) {
	hasOffsets := false
	for _, rows := range offsets {
		if len(rows) > 0 {
			hasOffsets = true
			break
		}
	}
	if !hasOffsets {
		return nil, "no_offsets"
	}

	header, err := parsePccHeader(data)
	if err != nil {
		return nil, "parse_header_failed"
	}
	compressedFlagStillSet := false
	if header.Flags&compressedFlag != 0 {
		decompressed, decompressErr := decompressME2OT(data)
		if decompressErr != nil {
			return nil, "decompress_failed"
		}
		data = decompressed
		header, err = parsePccHeader(data)
		if err != nil {
			return nil, "parse_header_after_decompress_failed"
		}
		if header.Flags&compressedFlag != 0 {
			compressedFlagStillSet = true
		}
	}
	names, err := parsePccNames(data, header)
	if err != nil {
		return nil, "parse_names_failed"
	}
	imports, err := parsePccImports(data, header)
	if err != nil {
		return nil, "parse_imports_failed"
	}
	exports, err := parsePccExports(data, header)
	if err != nil {
		return nil, "parse_exports_failed"
	}
	resolveExportNames(exports, imports, names)

	hits := []ContainerHit{}
	for strref, strrefOffsets := range offsets {
		for _, absoluteOffset := range strrefOffsets {
			best := bestContainingExport(exports, absoluteOffset, len(data))
			if best == nil {
				continue
			}
			hits = append(hits, ContainerHit{
				StrRef:         strref,
				AbsoluteOffset: absoluteOffset,
				LocalOffset:    absoluteOffset - best.SerialOffset,
				ExportIndex:    best.Index,
				ExportName:     best.ObjectName,
				ClassName:      best.ClassName,
				SerialOffset:   best.SerialOffset,
				SerialSize:     best.SerialSize,
			})
		}
	}
	if len(hits) == 0 {
		return nil, "no_matching_export"
	}
	if compressedFlagStillSet {
		return hits, "ok_after_forced_decompress"
	}
	return hits, "ok"
}

func decompressME2OT(data []byte) ([]byte, error) {
	cursor, err := locateCompressionInfoOffsetME2OT(data)
	if err != nil {
		return nil, err
	}
	if cursor+8 > len(data) {
		return nil, errors.New("compression header out of range")
	}
	compressionType := readI32(data, cursor)
	numChunks := readI32(data, cursor+4)
	cursor += 8
	if compressionType != compressionLZO {
		return nil, errors.New("unsupported compression type")
	}
	if numChunks <= 0 {
		return nil, errors.New("invalid chunk count")
	}

	type chunkInfo struct {
		uncompressedOffset int
		uncompressedSize   int
		compressedOffset   int
		compressedSize     int
	}
	chunks := make([]chunkInfo, 0, numChunks)
	for i := 0; i < numChunks; i++ {
		if cursor+16 > len(data) {
			return nil, errors.New("chunk table out of range")
		}
		chunks = append(chunks, chunkInfo{
			uncompressedOffset: readI32(data, cursor),
			uncompressedSize:   readI32(data, cursor+4),
			compressedOffset:   readI32(data, cursor+8),
			compressedSize:     readI32(data, cursor+12),
		})
		cursor += 16
	}

	firstChunkOffset := chunks[0].uncompressedOffset
	maxEnd := 0
	for _, c := range chunks {
		if c.uncompressedOffset < firstChunkOffset {
			firstChunkOffset = c.uncompressedOffset
		}
		end := c.uncompressedOffset + c.uncompressedSize
		if end > maxEnd {
			maxEnd = end
		}
	}
	if firstChunkOffset < 0 || maxEnd <= 0 || firstChunkOffset > len(data) {
		return nil, errors.New("invalid chunk offsets")
	}

	output := make([]byte, maxEnd)
	copy(output[:firstChunkOffset], data[:firstChunkOffset])

	for _, c := range chunks {
		if c.compressedOffset < 0 || c.compressedOffset+c.compressedSize > len(data) {
			return nil, errors.New("compressed chunk out of range")
		}
		chunkBlob := data[c.compressedOffset : c.compressedOffset+c.compressedSize]
		if len(chunkBlob) < chunkHeaderSize {
			return nil, errors.New("truncated chunk header")
		}
		magic := readU32(chunkBlob, 0)
		blockSize := readI32(chunkBlob, 4)
		compressedSizeHeader := readI32(chunkBlob, 8)
		uncompressedSizeHeader := readI32(chunkBlob, 12)
		if magic != chunkHeaderMagic {
			return nil, errors.New("invalid chunk magic")
		}
		if uncompressedSizeHeader != c.uncompressedSize {
			return nil, errors.New("chunk size mismatch")
		}
		if compressedSizeHeader+chunkHeaderSize > c.compressedSize {
			return nil, errors.New("truncated chunk payload")
		}
		if blockSize <= 0 {
			return nil, errors.New("invalid block size")
		}

		blockCount := uncompressedSizeHeader / blockSize
		if uncompressedSizeHeader%blockSize != 0 {
			blockCount++
		}
		blockTableOffset := chunkHeaderSize
		blockDataOffset := blockTableOffset + (blockCount * chunkBlockHeaderSize)
		if blockDataOffset > len(chunkBlob) {
			return nil, errors.New("invalid block table")
		}

		writeOffset := c.uncompressedOffset
		dataCursor := blockDataOffset
		for i := 0; i < blockCount; i++ {
			blockHeaderOffset := blockTableOffset + (i * chunkBlockHeaderSize)
			if blockHeaderOffset+8 > len(chunkBlob) {
				return nil, errors.New("block header out of range")
			}
			blockCompressedSize := readI32(chunkBlob, blockHeaderOffset)
			blockUncompressedSize := readI32(chunkBlob, blockHeaderOffset+4)
			if blockCompressedSize < 0 || blockUncompressedSize < 0 {
				return nil, errors.New("invalid block sizes")
			}
			if dataCursor+blockCompressedSize > len(chunkBlob) {
				return nil, errors.New("compressed block out of range")
			}

			compressedBlock := chunkBlob[dataCursor : dataCursor+blockCompressedSize]
			dataCursor += blockCompressedSize
			decompressedBlock := make([]byte, blockUncompressedSize)
			written, decErr := lzo.Decompress(compressedBlock, decompressedBlock)
			if decErr != nil {
				return nil, decErr
			}
			if written != blockUncompressedSize {
				return nil, errors.New("decompressed block size mismatch")
			}
			endOffset := writeOffset + blockUncompressedSize
			if endOffset > len(output) {
				return nil, errors.New("decompressed output out of range")
			}
			copy(output[writeOffset:endOffset], decompressedBlock)
			writeOffset = endOffset
		}
	}

	return output, nil
}

func locateCompressionInfoOffsetME2OT(data []byte) (int, error) {
	cursor := 8
	if cursor+4 > len(data) {
		return 0, errors.New("truncated header")
	}
	cursor += 4 // full_header_size
	folderLen := readI32(data, cursor)
	cursor += 4
	if folderLen > 0 {
		cursor += folderLen
	} else if folderLen < 0 {
		cursor += (-folderLen) * 2
	}
	if cursor+4 > len(data) {
		return 0, errors.New("truncated header folder")
	}
	cursor += 4  // flags
	cursor += 24 // name/export/import pairs
	cursor += 4  // dependency table offset
	cursor += 16 // package guid
	if cursor+4 > len(data) {
		return 0, errors.New("truncated generations")
	}
	generations := int(readU32(data, cursor))
	cursor += 4
	if generations > 0 {
		cursor += 12
		cursor += (generations - 1) * 12
	}
	cursor += 8  // engine_version, cooked_content_version
	cursor += 16 // me2 pc extra header block
	cursor += 8  // build + branch
	if cursor < 0 || cursor > len(data) {
		return 0, errors.New("compression info out of range")
	}
	return cursor, nil
}

func parsePccHeader(data []byte) (pccHeader, error) {
	if len(data) < 44 {
		return pccHeader{}, errors.New("file too small")
	}
	if readU32(data, 0) != mePackageMagic {
		return pccHeader{}, errors.New("invalid magic")
	}
	versionPack := readU32(data, 4)
	unrealVersion := int(versionPack & 0xFFFF)
	licenseeVersion := int((versionPack >> 16) & 0xFFFF)
	cursor := 8
	cursor += 4 // full header size
	folderLen := readI32(data, cursor)
	cursor += 4
	if folderLen > 0 {
		cursor += folderLen
	} else if folderLen < 0 {
		cursor += (-folderLen) * 2
	}
	if cursor < 0 || cursor+28 > len(data) {
		return pccHeader{}, errors.New("truncated header")
	}
	flags := readU32(data, cursor)
	cursor += 4
	nameCount := readI32(data, cursor)
	cursor += 4
	nameOffset := readI32(data, cursor)
	cursor += 4
	exportCount := readI32(data, cursor)
	cursor += 4
	exportOffset := readI32(data, cursor)
	cursor += 4
	importCount := readI32(data, cursor)
	cursor += 4
	importOffset := readI32(data, cursor)
	if nameCount < 0 || exportCount < 0 || importCount < 0 {
		return pccHeader{}, errors.New("negative table count")
	}
	return pccHeader{
		UnrealVersion:   unrealVersion,
		LicenseeVersion: licenseeVersion,
		Flags:           flags,
		NameCount:       nameCount,
		NameOffset:      nameOffset,
		ExportCount:     exportCount,
		ExportOffset:    exportOffset,
		ImportCount:     importCount,
		ImportOffset:    importOffset,
	}, nil
}

func parsePccNames(data []byte, header pccHeader) ([]string, error) {
	names := make([]string, 0, header.NameCount)
	cursor := header.NameOffset
	for i := 0; i < header.NameCount; i++ {
		text, next, err := readUnrealString(data, cursor)
		if err != nil {
			return nil, err
		}
		cursor = next
		if header.UnrealVersion <= 491 {
			cursor += 8
		} else {
			cursor += 4
		}
		if cursor > len(data) {
			return nil, errors.New("name table out of range")
		}
		names = append(names, text)
	}
	return names, nil
}

func parsePccImports(data []byte, header pccHeader) ([]pccImport, error) {
	imports := make([]pccImport, 0, header.ImportCount)
	cursor := header.ImportOffset
	for i := 0; i < header.ImportCount; i++ {
		if cursor+28 > len(data) {
			return nil, errors.New("truncated import table")
		}
		imports = append(imports, pccImport{
			ClassNameIndex:  readI32(data, cursor+8),
			ObjectNameIndex: readI32(data, cursor+20),
		})
		cursor += 28
	}
	return imports, nil
}

func parsePccExports(data []byte, header pccHeader) ([]pccExport, error) {
	exports := make([]pccExport, 0, header.ExportCount)
	cursor := header.ExportOffset
	for i := 0; i < header.ExportCount; i++ {
		if cursor+40 > len(data) {
			return nil, errors.New("truncated export table")
		}

		classIndex := readI32(data, cursor)
		objectNameIndex := readI32(data, cursor+12)
		serialSize := readI32(data, cursor+32)
		serialOffset := readI32(data, cursor+36)

		headerLen := 40
		if header.UnrealVersion <= 512 {
			if cursor+44 > len(data) {
				return nil, errors.New("truncated export component map")
			}
			componentCount := readI32(data, cursor+40)
			if componentCount < 0 {
				return nil, errors.New("negative component map count")
			}
			headerLen += 4 + (componentCount * 12)
		}

		if cursor+headerLen+8 > len(data) {
			return nil, errors.New("truncated export generation header")
		}
		generationCount := readI32(data, cursor+headerLen+4)
		if generationCount < 0 {
			return nil, errors.New("negative generation count")
		}
		headerLen += 8 + (generationCount * 4) + 16
		if !(header.UnrealVersion == 491 && header.LicenseeVersion <= 110) {
			headerLen += 4
		}
		if cursor+headerLen > len(data) {
			return nil, errors.New("truncated export footer")
		}

		exports = append(exports, pccExport{
			Index:           i,
			ClassIndex:      classIndex,
			ObjectNameIndex: objectNameIndex,
			SerialSize:      serialSize,
			SerialOffset:    serialOffset,
		})
		cursor += headerLen
	}
	return exports, nil
}

func resolveExportNames(exports []pccExport, imports []pccImport, names []string) {
	for i := range exports {
		exports[i].ObjectName = resolveName(exports[i].ObjectNameIndex, names)
		classIndex := exports[i].ClassIndex
		if classIndex > 0 {
			idx := classIndex - 1
			if idx >= 0 && idx < len(exports) {
				exports[i].ClassName = resolveName(exports[idx].ObjectNameIndex, names)
			}
		} else if classIndex < 0 {
			idx := (-classIndex) - 1
			if idx >= 0 && idx < len(imports) {
				exports[i].ClassName = resolveName(imports[idx].ObjectNameIndex, names)
			}
		}
	}
}

func bestContainingExport(exports []pccExport, offset int, dataLen int) *pccExport {
	var best *pccExport
	for i := range exports {
		item := &exports[i]
		start := item.SerialOffset
		end := item.SerialOffset + item.SerialSize
		if start < 0 || end > dataLen || start >= end {
			continue
		}
		if offset < start || offset >= end {
			continue
		}
		if best == nil {
			best = item
			continue
		}
		itemHasClass := item.ClassName != ""
		bestHasClass := best.ClassName != ""
		if itemHasClass && !bestHasClass {
			best = item
			continue
		}
		if itemHasClass == bestHasClass && item.SerialSize < best.SerialSize {
			best = item
		}
	}
	return best
}

func readUnrealString(data []byte, offset int) (string, int, error) {
	if offset < 0 || offset+4 > len(data) {
		return "", offset, errors.New("string offset out of range")
	}
	count := readI32(data, offset)
	cursor := offset + 4
	if count == 0 {
		return "", cursor, nil
	}
	if count > 0 {
		end := cursor + count
		if end > len(data) {
			return "", cursor, errors.New("truncated ascii string")
		}
		raw := data[cursor:end]
		if len(raw) > 0 && raw[len(raw)-1] == 0 {
			raw = raw[:len(raw)-1]
		}
		return string(raw), end, nil
	}
	charCount := -count
	end := cursor + (charCount * 2)
	if end > len(data) {
		return "", cursor, errors.New("truncated utf16 string")
	}
	raw := data[cursor:end]
	if len(raw) >= 2 && raw[len(raw)-2] == 0 && raw[len(raw)-1] == 0 {
		raw = raw[:len(raw)-2]
	}
	if len(raw)%2 != 0 {
		return "", cursor, errors.New("invalid utf16 size")
	}
	units := make([]uint16, len(raw)/2)
	for i := 0; i < len(units); i++ {
		units[i] = binary.LittleEndian.Uint16(raw[i*2 : i*2+2])
	}
	return string(utf16.Decode(units)), end, nil
}

func resolveName(index int, names []string) string {
	if index >= 0 && index < len(names) {
		return names[index]
	}
	return ""
}

func readI32(data []byte, offset int) int {
	return int(int32(binary.LittleEndian.Uint32(data[offset : offset+4])))
}

func readU32(data []byte, offset int) uint32 {
	return binary.LittleEndian.Uint32(data[offset : offset+4])
}
