package scan

type Result struct {
	Path      string
	Size      int64
	ModTimeNs int64
	Hits      []int
	Offsets   map[int][]int
	Err       string
}

type FileEntry struct {
	Path      string        `json:"path"`
	Size      int64         `json:"size"`
	ModTimeNs int64         `json:"mod_time_ns"`
	Hits      []int         `json:"hits"`
	Offsets   map[int][]int `json:"offsets,omitempty"`
	Error     string        `json:"error,omitempty"`
}

type Report struct {
	Version           string                   `json:"version"`
	RootBioGame       string                   `json:"root_biogame"`
	TargetStrRef      []int                    `json:"target_strrefs"`
	FilesScanned      int                      `json:"files_scanned"`
	FilesReused       int                      `json:"files_reused"`
	FilesRescanned    int                      `json:"files_rescanned"`
	Candidates        []string                 `json:"candidates"`
	HitsByFile        map[string][]int         `json:"hits_by_file"`
	OffsetsByFile     map[string]map[int][]int `json:"offsets_by_file,omitempty"`
	Errors            []map[string]string      `json:"errors"`
	GeneratedAt       string                   `json:"generated_at"`
	Entries           []FileEntry              `json:"entries,omitempty"`
	IncrementalSource string                   `json:"incremental_source,omitempty"`
}
