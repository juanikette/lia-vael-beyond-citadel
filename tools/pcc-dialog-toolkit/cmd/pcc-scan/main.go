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
)

type result struct {
	Path string
	Hits []int
	Err  string
}

type report struct {
	Version      string              `json:"version"`
	RootBioGame  string              `json:"root_biogame"`
	TargetStrRef []int               `json:"target_strrefs"`
	FilesScanned int                 `json:"files_scanned"`
	Candidates   []string            `json:"candidates"`
	HitsByFile   map[string][]int    `json:"hits_by_file"`
	Errors       []map[string]string `json:"errors"`
}

func main() {
	root := flag.String("root-biogame", "", "Path to BioGame root")
	out := flag.String("out", "candidate-index.json", "Output JSON path")
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
	results := scan(files, strrefs, *workers)

	rep := report{
		Version:      "1",
		RootBioGame:  *root,
		TargetStrRef: strrefs,
		FilesScanned: len(files),
		Candidates:   []string{},
		HitsByFile:   map[string][]int{},
		Errors:       []map[string]string{},
	}

	for _, r := range results {
		if r.Err != "" {
			rep.Errors = append(rep.Errors, map[string]string{"file": r.Path, "error": r.Err})
			continue
		}
		if len(r.Hits) == 0 {
			continue
		}
		rep.Candidates = append(rep.Candidates, r.Path)
		rep.HitsByFile[r.Path] = r.Hits
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
	fmt.Printf("files_scanned=%d candidates=%d errors=%d\n", rep.FilesScanned, len(rep.Candidates), len(rep.Errors))
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
				blob, err := os.ReadFile(path)
				if err != nil {
					out <- result{Path: path, Err: err.Error()}
					continue
				}
				hits := []int{}
				for _, s := range strrefs {
					if bytesContains(blob, sigs[s]) {
						hits = append(hits, s)
					}
				}
				out <- result{Path: path, Hits: hits}
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
