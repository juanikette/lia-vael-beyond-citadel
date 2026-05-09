package scan

import (
	"bytes"
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
				offsetsByStrref := map[int][]int{}
				for _, s := range strrefs {
					offsets := findOffsets(blob, sigs[s], 32)
					if len(offsets) > 0 {
						hits = append(hits, s)
						offsetsByStrref[s] = offsets
					}
				}
				containers, containerStatus := mapOffsetsToContainers(blob, offsetsByStrref)
				out <- Result{Path: path, Size: info.Size(), ModTimeNs: info.ModTime().UnixNano(), Hits: hits, Offsets: offsetsByStrref, Containers: containers, ContainerStatus: containerStatus}
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

func findOffsets(haystack []byte, needle []byte, maxOffsets int) []int {
	offsets := []int{}
	if len(needle) == 0 || len(haystack) < len(needle) {
		return offsets
	}
	searchFrom := 0
	for searchFrom <= len(haystack)-len(needle) {
		foundAt := bytes.Index(haystack[searchFrom:], needle)
		if foundAt < 0 {
			break
		}
		absolute := searchFrom + foundAt
		offsets = append(offsets, absolute)
		if maxOffsets > 0 && len(offsets) >= maxOffsets {
			return offsets
		}
		searchFrom = absolute + 1
	}
	return offsets
}
