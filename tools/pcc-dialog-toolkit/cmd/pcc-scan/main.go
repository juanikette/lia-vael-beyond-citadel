package main

import (
	"encoding/binary"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"
)

type result struct {
	Path      string
	Size      int64
	ModTimeNs int64
	Hits      []int
	Err       string
}

type fileEntry struct {
	Path      string `json:"path"`
	Size      int64  `json:"size"`
	ModTimeNs int64  `json:"mod_time_ns"`
	Hits      []int  `json:"hits"`
	Error     string `json:"error,omitempty"`
}

type report struct {
	Version           string              `json:"version"`
	RootBioGame       string              `json:"root_biogame"`
	TargetStrRef      []int               `json:"target_strrefs"`
	FilesScanned      int                 `json:"files_scanned"`
	FilesReused       int                 `json:"files_reused"`
	FilesRescanned    int                 `json:"files_rescanned"`
	Candidates        []string            `json:"candidates"`
	HitsByFile        map[string][]int    `json:"hits_by_file"`
	Errors            []map[string]string `json:"errors"`
	GeneratedAt       string              `json:"generated_at"`
	Entries           []fileEntry         `json:"entries,omitempty"`
	IncrementalSource string              `json:"incremental_source,omitempty"`
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

	strrefs, err := parseStrrefs(strrefArgs)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}

	files := collectPccFiles(*root)
	previous := map[string]fileEntry{}
	incrementalSource := ""
	if *index != "" {
		loaded, loadErr := loadIndex(*index)
		if loadErr == nil {
			for _, item := range loaded.Entries {
				previous[item.Path] = item
			}
			incrementalSource = *index
		}
	}

	toScan, reused := splitChangedFiles(files, previous)
	results := scan(toScan, strrefs, *workers)

	rep := report{
		Version:           "2",
		RootBioGame:       *root,
		TargetStrRef:      strrefs,
		FilesScanned:      len(files),
		FilesReused:       len(reused),
		FilesRescanned:    len(toScan),
		Candidates:        []string{},
		HitsByFile:        map[string][]int{},
		Errors:            []map[string]string{},
		GeneratedAt:       time.Now().UTC().Format(time.RFC3339),
		Entries:           []fileEntry{},
		IncrementalSource: incrementalSource,
	}

	state := map[string]fileEntry{}
	for _, item := range reused {
		state[item.Path] = item
	}

	for _, r := range results {
		entry := fileEntry{Path: r.Path, Size: r.Size, ModTimeNs: r.ModTimeNs, Hits: r.Hits, Error: r.Err}
		state[r.Path] = entry
		if r.Err != "" {
			rep.Errors = append(rep.Errors, map[string]string{"file": r.Path, "error": r.Err})
		}
	}

	for _, path := range sortedPaths(state) {
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

func parseStrrefs(raw []string) ([]int, error) {
	seen := map[int]struct{}{}
	rows := []int{}
	for _, s := range raw {
		var v int
		_, err := fmt.Sscanf(strings.TrimSpace(s), "%d", &v)
		if err != nil || v < 0 {
			return nil, fmt.Errorf("invalid strref: %q", s)
		}
		if _, ok := seen[v]; ok {
			continue
		}
		seen[v] = struct{}{}
		rows = append(rows, v)
	}
	sort.Ints(rows)
	return rows, nil
}

func collectPccFiles(root string) []string {
	files := []string{}
	cooked := filepath.Join(root, "CookedPC")
	_ = filepath.WalkDir(cooked, func(path string, d os.DirEntry, err error) error {
		if err == nil && !d.IsDir() && strings.EqualFold(filepath.Ext(path), ".pcc") {
			files = append(files, path)
		}
		return nil
	})
	dlc := filepath.Join(root, "DLC")
	_ = filepath.WalkDir(dlc, func(path string, d os.DirEntry, err error) error {
		if err == nil && !d.IsDir() && strings.EqualFold(filepath.Ext(path), ".pcc") {
			files = append(files, path)
		}
		return nil
	})
	sort.Strings(files)
	return files
}

func loadIndex(path string) (*report, error) {
	blob, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var rep report
	if err := json.Unmarshal(blob, &rep); err != nil {
		return nil, err
	}
	return &rep, nil
}

func splitChangedFiles(files []string, previous map[string]fileEntry) ([]string, []fileEntry) {
	toScan := []string{}
	reused := []fileEntry{}
	for _, path := range files {
		info, err := os.Stat(path)
		if err != nil {
			toScan = append(toScan, path)
			continue
		}
		prev, ok := previous[path]
		if !ok {
			toScan = append(toScan, path)
			continue
		}
		if prev.Size != info.Size() || prev.ModTimeNs != info.ModTime().UnixNano() {
			toScan = append(toScan, path)
			continue
		}
		reused = append(reused, prev)
	}
	return toScan, reused
}

func sortedPaths(state map[string]fileEntry) []string {
	keys := make([]string, 0, len(state))
	for k := range state {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func scan(files []string, strrefs []int, workers int) []result {
	if workers < 1 {
		workers = 1
	}
	sigs := make(map[int][]byte, len(strrefs))
	for _, s := range strrefs {
		buf := make([]byte, 4)
		binary.LittleEndian.PutUint32(buf, uint32(int32(s)))
		sigs[s] = buf
	}

	jobs := make(chan string)
	out := make(chan result)
	var wg sync.WaitGroup
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for path := range jobs {
				info, statErr := os.Stat(path)
				if statErr != nil {
					out <- result{Path: path, Err: statErr.Error()}
					continue
				}
				blob, err := os.ReadFile(path)
				if err != nil {
					out <- result{Path: path, Size: info.Size(), ModTimeNs: info.ModTime().UnixNano(), Err: err.Error()}
					continue
				}
				hits := []int{}
				for _, s := range strrefs {
					if bytesContains(blob, sigs[s]) {
						hits = append(hits, s)
					}
				}
				out <- result{Path: path, Size: info.Size(), ModTimeNs: info.ModTime().UnixNano(), Hits: hits}
			}
		}()
	}

	go func() {
		for _, f := range files {
			jobs <- f
		}
		close(jobs)
		wg.Wait()
		close(out)
	}()

	rows := make([]result, 0, len(files))
	for r := range out {
		rows = append(rows, r)
	}
	return rows
}

func bytesContains(haystack []byte, needle []byte) bool {
	if len(needle) == 0 || len(haystack) < len(needle) {
		return false
	}
	for i := 0; i <= len(haystack)-len(needle); i++ {
		ok := true
		for j := 0; j < len(needle); j++ {
			if haystack[i+j] != needle[j] {
				ok = false
				break
			}
		}
		if ok {
			return true
		}
	}
	return false
}
