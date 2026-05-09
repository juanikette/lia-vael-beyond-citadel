package scan

import (
	"reflect"
	"testing"
)

func TestParseStrrefsSortsAndDeduplicates(t *testing.T) {
	got, err := ParseStrrefs([]string{"42", "7", "42", " 10 "})
	if err != nil {
		t.Fatalf("ParseStrrefs returned error: %v", err)
	}
	want := []int{7, 10, 42}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("unexpected values: got=%v want=%v", got, want)
	}
}

func TestParseStrrefsRejectsInvalidValue(t *testing.T) {
	if _, err := ParseStrrefs([]string{"ok", "-1"}); err == nil {
		t.Fatal("expected ParseStrrefs to fail for invalid input")
	}
}
