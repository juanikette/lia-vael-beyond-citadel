package scan

import (
	"encoding/binary"
	"fmt"
	"os"
	"sort"
	"strings"
	"sync"
)

func ParseStrrefs(raw []string) ([]int, error) {
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

func Run(files []string, strrefs []int, workers int) []Result {
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
	out := make(chan Result)
	var wg sync.WaitGroup
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for path := range jobs {
				info, statErr := os.Stat(path)
				if statErr != nil {
					out <- Result{Path: path, Err: statErr.Error()}
					continue
				}
				blob, err := os.ReadFile(path)
				if err != nil {
					out <- Result{Path: path, Size: info.Size(), ModTimeNs: info.ModTime().UnixNano(), Err: err.Error()}
					continue
				}
				hits := []int{}
				for _, s := range strrefs {
					if bytesContains(blob, sigs[s]) {
						hits = append(hits, s)
					}
				}
				out <- Result{Path: path, Size: info.Size(), ModTimeNs: info.ModTime().UnixNano(), Hits: hits}
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

	rows := make([]Result, 0, len(files))
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
