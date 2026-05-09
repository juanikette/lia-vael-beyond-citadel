package scan

import (
	"encoding/json"
	"os"
	"sort"
)

func RequiredCapabilities() []string {
	return []string{"strref_offsets_v1", "containers_v1"}
}

func LoadIndex(path string) (*Report, error) {
	blob, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var rep Report
	if err := json.Unmarshal(blob, &rep); err != nil {
		return nil, err
	}
	return &rep, nil
}

func HasCapabilities(rep *Report, required []string) bool {
	if rep == nil {
		return false
	}
	available := map[string]struct{}{}
	for _, capability := range rep.Capabilities {
		available[capability] = struct{}{}
	}
	for _, capability := range required {
		if _, ok := available[capability]; !ok {
			return false
		}
	}
	return true
}

func SplitChangedFiles(files []string, previous map[string]FileEntry) ([]string, []FileEntry) {
	toScan := []string{}
	reused := []FileEntry{}
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

func SortedPaths(state map[string]FileEntry) []string {
	keys := make([]string, 0, len(state))
	for k := range state {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}
