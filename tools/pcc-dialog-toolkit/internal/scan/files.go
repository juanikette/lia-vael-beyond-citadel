package scan

import (
	"path/filepath"
	"sort"
	"strings"

	"os"
)

func CollectPccFiles(root string) []string {
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
