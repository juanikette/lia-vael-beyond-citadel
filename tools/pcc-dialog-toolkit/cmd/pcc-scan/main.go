package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"runtime"
	"sort"
	"strings"
	"time"

	"pcc-dialog-toolkit-go/internal/scan"
)

type report struct {
	Version           string                         `json:"version"`
	Capabilities      []string                       `json:"capabilities,omitempty"`
	RootBioGame       string                         `json:"root_biogame"`
	TargetStrRef      []int                          `json:"target_strrefs"`
	FilesScanned      int                            `json:"files_scanned"`
	FilesReused       int                            `json:"files_reused"`
	FilesRescanned    int                            `json:"files_rescanned"`
	Candidates        []string                       `json:"candidates"`
	HitsByFile        map[string][]int               `json:"hits_by_file"`
	OffsetsByFile     map[string]map[int][]int       `json:"offsets_by_file,omitempty"`
	ContainersByFile  map[string][]scan.ContainerHit `json:"containers_by_file,omitempty"`
	Errors            []map[string]string            `json:"errors"`
	GeneratedAt       string                         `json:"generated_at"`
	Entries           []scan.FileEntry               `json:"entries,omitempty"`
	IncrementalSource string                         `json:"incremental_source,omitempty"`
}

func main() {
	root := flag.String("root-biogame", "", "Path to BioGame root")
	out := flag.String("out", "candidate-index.json", "Output JSON path")
	index := flag.String("index", "", "Existing index JSON path for incremental refresh")
	workers := flag.Int("workers", runtime.NumCPU(), "Worker count")
	strrefArgs := multiFlag{}
	flag.Var(&strrefArgs, "strref", "Target StrRef (repeatable)")
	flag.Parse()

	if *root == "" {
		fmt.Fprintln(os.Stderr, "--root-biogame is required")
		os.Exit(2)
	}
	if len(strrefArgs) == 0 {
		fmt.Fprintln(os.Stderr, "At least one --strref is required")
		os.Exit(2)
	}

	strrefs, err := scan.ParseStrrefs(strrefArgs)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}

	files := scan.CollectPccFiles(*root)
	previous := map[string]scan.FileEntry{}
	incrementalSource := ""
	if *index != "" {
		loaded, loadErr := scan.LoadIndex(*index)
		if loadErr == nil && scan.HasCapabilities(loaded, scan.RequiredCapabilities()) {
			for _, item := range loaded.Entries {
				previous[item.Path] = item
			}
			incrementalSource = *index
		}
	}

	toScan, reused := scan.SplitChangedFiles(files, previous)
	results := scan.Run(toScan, strrefs, *workers)

	rep := report{
		Version:           "3",
		Capabilities:      scan.RequiredCapabilities(),
		RootBioGame:       *root,
		TargetStrRef:      strrefs,
		FilesScanned:      len(files),
		FilesReused:       len(reused),
		FilesRescanned:    len(toScan),
		Candidates:        []string{},
		HitsByFile:        map[string][]int{},
		OffsetsByFile:     map[string]map[int][]int{},
		ContainersByFile:  map[string][]scan.ContainerHit{},
		Errors:            []map[string]string{},
		GeneratedAt:       time.Now().UTC().Format(time.RFC3339),
		Entries:           []scan.FileEntry{},
		IncrementalSource: incrementalSource,
	}

	state := map[string]scan.FileEntry{}
	for _, item := range reused {
		state[item.Path] = item
	}

	for _, r := range results {
		entry := scan.FileEntry{Path: r.Path, Size: r.Size, ModTimeNs: r.ModTimeNs, Hits: r.Hits, Offsets: r.Offsets, Containers: r.Containers, Error: r.Err}
		state[r.Path] = entry
		if r.Err != "" {
			rep.Errors = append(rep.Errors, map[string]string{"file": r.Path, "error": r.Err})
		}
	}

	for _, path := range scan.SortedPaths(state) {
		item := state[path]
		rep.Entries = append(rep.Entries, item)
		if item.Error != "" {
			continue
		}
		if len(item.Hits) == 0 {
			continue
		}
		rep.Candidates = append(rep.Candidates, item.Path)
		rep.HitsByFile[item.Path] = item.Hits
		if len(item.Offsets) > 0 {
			rep.OffsetsByFile[item.Path] = item.Offsets
		}
		if len(item.Containers) > 0 {
			rep.ContainersByFile[item.Path] = item.Containers
		}
	}

	sort.Strings(rep.Candidates)
	data, err := json.MarshalIndent(rep, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := os.WriteFile(*out, append(data, '\n'), 0o644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	fmt.Printf("candidate index written: %s\n", *out)
	fmt.Printf(
		"files_scanned=%d reused=%d rescanned=%d candidates=%d errors=%d\n",
		rep.FilesScanned,
		rep.FilesReused,
		rep.FilesRescanned,
		len(rep.Candidates),
		len(rep.Errors),
	)
}

type multiFlag []string

func (m *multiFlag) String() string { return strings.Join(*m, ",") }
func (m *multiFlag) Set(v string) error {
	*m = append(*m, v)
	return nil
}
