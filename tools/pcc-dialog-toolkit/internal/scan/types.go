package scan

type Result struct {
	Path       string
	Size       int64
	ModTimeNs  int64
	Hits       []int
	Offsets    map[int][]int
	Containers []ContainerHit
	Err        string
}

type FileEntry struct {
	Path       string         `json:"path"`
	Size       int64          `json:"size"`
	ModTimeNs  int64          `json:"mod_time_ns"`
	Hits       []int          `json:"hits"`
	Offsets    map[int][]int  `json:"offsets,omitempty"`
	Containers []ContainerHit `json:"containers,omitempty"`
	Error      string         `json:"error,omitempty"`
}

type ContainerHit struct {
	StrRef         int    `json:"strref"`
	AbsoluteOffset int    `json:"absolute_offset"`
	LocalOffset    int    `json:"local_offset"`
	ExportIndex    int    `json:"export_index"`
	ExportName     string `json:"export_name,omitempty"`
	ClassName      string `json:"class_name,omitempty"`
	SerialOffset   int    `json:"serial_offset"`
	SerialSize     int    `json:"serial_size"`
}

type Report struct {
	Version           string                    `json:"version"`
	Capabilities      []string                  `json:"capabilities,omitempty"`
	RootBioGame       string                    `json:"root_biogame"`
	TargetStrRef      []int                     `json:"target_strrefs"`
	FilesScanned      int                       `json:"files_scanned"`
	FilesReused       int                       `json:"files_reused"`
	FilesRescanned    int                       `json:"files_rescanned"`
	Candidates        []string                  `json:"candidates"`
	HitsByFile        map[string][]int          `json:"hits_by_file"`
	OffsetsByFile     map[string]map[int][]int  `json:"offsets_by_file,omitempty"`
	ContainersByFile  map[string][]ContainerHit `json:"containers_by_file,omitempty"`
	Errors            []map[string]string       `json:"errors"`
	GeneratedAt       string                    `json:"generated_at"`
	Entries           []FileEntry               `json:"entries,omitempty"`
	IncrementalSource string                    `json:"incremental_source,omitempty"`
}
