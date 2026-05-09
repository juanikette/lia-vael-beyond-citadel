package scan

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestSplitChangedFilesReusesAndRescans(t *testing.T) {
	tmp := t.TempDir()
	keep := filepath.Join(tmp, "keep.pcc")
	change := filepath.Join(tmp, "change.pcc")
	newFile := filepath.Join(tmp, "new.pcc")

	if err := os.WriteFile(keep, []byte("AAAA"), 0o644); err != nil {
		t.Fatalf("write keep: %v", err)
	}
	if err := os.WriteFile(change, []byte("BBBB"), 0o644); err != nil {
		t.Fatalf("write change: %v", err)
	}
	if err := os.WriteFile(newFile, []byte("CCCC"), 0o644); err != nil {
		t.Fatalf("write new: %v", err)
	}

	keepInfo, err := os.Stat(keep)
	if err != nil {
		t.Fatalf("stat keep: %v", err)
	}
	changeInfo, err := os.Stat(change)
	if err != nil {
		t.Fatalf("stat change: %v", err)
	}

	previous := map[string]FileEntry{
		keep: {
			Path:      keep,
			Size:      keepInfo.Size(),
			ModTimeNs: keepInfo.ModTime().UnixNano(),
			Hits:      []int{1},
		},
		change: {
			Path:      change,
			Size:      changeInfo.Size(),
			ModTimeNs: changeInfo.ModTime().UnixNano(),
			Hits:      []int{2},
		},
	}

	time.Sleep(10 * time.Millisecond)
	if err := os.WriteFile(change, []byte("BBBB-updated"), 0o644); err != nil {
		t.Fatalf("update change: %v", err)
	}

	toScan, reused := SplitChangedFiles([]string{keep, change, newFile}, previous)
	if len(reused) != 1 || reused[0].Path != keep {
		t.Fatalf("unexpected reused entries: %#v", reused)
	}
	if len(toScan) != 2 {
		t.Fatalf("unexpected toScan size: %d (%v)", len(toScan), toScan)
	}

	seen := map[string]bool{}
	for _, path := range toScan {
		seen[path] = true
	}
	if !seen[change] || !seen[newFile] {
		t.Fatalf("expected changed and new files in toScan: %v", toScan)
	}
}

func TestHasCapabilitiesRequiresAllCapabilities(t *testing.T) {
	rep := &Report{Capabilities: []string{"strref_offsets_v1", "other"}}
	if !HasCapabilities(rep, []string{"strref_offsets_v1"}) {
		t.Fatal("expected required capability to be present")
	}
	if HasCapabilities(rep, []string{"missing"}) {
		t.Fatal("expected missing capability to fail")
	}
}
