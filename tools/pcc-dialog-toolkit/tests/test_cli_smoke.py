import subprocess
import sys
from pathlib import Path

from cli import (
    _build_semantic_container_usages,
    _build_non_bioconversation_container_usages,
    _merge_strref_usages_with_container_fallback,
    _conversation_lia_vael_context,
    _conversation_match_reasons,
    _find_strref_usages,
    _load_candidate_index,
)
from model.ast import Conversation, EntryNode, ReplyNode, Speaker


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_help_returns_zero() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert "pcc_dialog_extract" in result.stdout


def test_version_returns_zero() -> None:
    result = run_cli("--version")
    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_conversation_match_reasons_detects_lia_reference() -> None:
    conversation = Conversation(
        id="citadel_quarian_followup",
        export_index=10,
        package_path="sample.pcc",
        game_profile="me2_ot",
        entries=[
            EntryNode(
                id=0,
                speaker_id=None,
                speaker_tag="Shepard",
                listener_tag="LiaVael",
                line_strref=1,
                line_text="I heard Lia'Vael is safe.",
                reply_links=[],
            )
        ],
        replies=[
            ReplyNode(
                id=0,
                line_strref=2,
                line_text="Good to hear.",
                target_entry_id=0,
                condition_refs=[],
            )
        ],
        speakers=[Speaker(id=0, tag="LiaVael", display_name="Lia'Vael")],
        parse_mode="row_payload",
        warnings=[],
    )

    reasons = _conversation_match_reasons(conversation, "lia")
    assert "entry_listener_tag" in reasons
    assert "entry_line_text" in reasons
    assert "speaker_tag" in reasons


def test_lia_vael_context_profile_scores_quarian_citadel_lines() -> None:
    conversation = Conversation(
        id="citadel_quarian_case",
        export_index=22,
        package_path="sample.pcc",
        game_profile="me2_ot",
        entries=[
            EntryNode(
                id=0,
                speaker_id=None,
                speaker_tag="C-Sec",
                listener_tag="Shepard",
                line_strref=10,
                line_text="A quarian on pilgrimage was accused near Zakera Ward on the Citadel.",
                reply_links=[],
            )
        ],
        replies=[],
        speakers=[Speaker(id=0, tag="C-Sec", display_name=None)],
        parse_mode="row_payload",
        warnings=[],
    )

    score, hits, snippets = _conversation_lia_vael_context(conversation)
    assert score >= 6
    assert "quarian" in hits
    assert "zakera" in hits
    assert snippets


def test_find_strref_usages_returns_entry_and_reply_matches() -> None:
    conversation = Conversation(
        id="conv_a",
        export_index=5,
        package_path="sample.pcc",
        game_profile="me2_ot",
        entries=[
            EntryNode(
                id=0,
                speaker_id=None,
                speaker_tag=None,
                listener_tag=None,
                line_strref=123,
                line_text="Entry line",
                reply_links=[],
            )
        ],
        replies=[
            ReplyNode(
                id=9,
                line_strref=456,
                line_text="Reply line",
                target_entry_id=0,
                condition_refs=[],
            )
        ],
        speakers=[],
        parse_mode="row_payload",
        warnings=[],
    )

    rows = _find_strref_usages([conversation], {123, 456, 999})
    assert len(rows) == 2
    assert any(row["kind"] == "entry" and row["strref"] == 123 for row in rows)
    assert any(row["kind"] == "reply" and row["strref"] == 456 for row in rows)
    assert all("source_container" in row for row in rows)
    assert all(row["source_container"]["class_name"] == "BioConversation" for row in rows)


def test_load_candidate_index_reads_candidates(tmp_path: Path) -> None:
    index_path = tmp_path / "candidates.json"
    index_path.write_text('{"candidates":["C:/a.pcc","C:/b.pcc"]}', encoding="utf-8")
    rows = _load_candidate_index(index_path)
    assert len(rows) == 2
    assert rows[0].name == "a.pcc"


def test_build_non_bioconversation_container_usages_maps_hits() -> None:
    raw_hits = [
        {
            "file": "C:/game/A_LOC_INT.pcc",
            "export_index": 10,
            "export_name": "SomeContainer",
            "class_name": None,
            "hits": [{"strref": 282425, "offsets": [12], "count": 1}],
        },
        {
            "file": "C:/game/B.pcc",
            "export_index": 11,
            "export_name": "BioConv",
            "class_name": "BioConversation",
            "hits": [{"strref": 123, "offsets": [3], "count": 1}],
        },
    ]

    rows = _build_non_bioconversation_container_usages(raw_hits)
    assert len(rows) == 1
    assert rows[0]["kind"] == "container"
    assert rows[0]["strref"] == 282425
    assert rows[0]["source_container"]["parse_mode"] == "raw_export_signature"


def test_merge_strref_usages_with_container_fallback_uses_container_when_empty() -> None:
    container_rows = [
        {
            "kind": "container",
            "file": "C:/x.pcc",
            "strref": 282425,
            "offsets": [9],
            "count": 1,
            "source_container": {
                "class_name": None,
                "export_index": 10,
                "export_name": "Tag",
                "parse_mode": "raw_export_signature",
            },
        }
    ]
    merged, source = _merge_strref_usages_with_container_fallback([], [], container_rows)
    assert source == "container_fallback"
    assert len(merged) == 1
    assert merged[0]["kind"] == "container"
    assert merged[0]["strref"] == 282425


def test_merge_strref_usages_with_container_fallback_keeps_bioconversation_rows() -> None:
    bioconv_rows = [{"kind": "entry", "strref": 123}]
    merged, source = _merge_strref_usages_with_container_fallback(bioconv_rows, [], [])
    assert source == "bioconversation"
    assert merged == bioconv_rows


def test_build_semantic_container_usages_maps_stringref_properties() -> None:
    semantic_hits = [
        {
            "file": "C:/game/A_LOC_INT.pcc",
            "export_index": 22,
            "export_name": "SFXSeqAct_ShowChoiceGUI_0",
            "class_name": "SFXSeqAct_ShowChoiceGUI",
            "hits": [
                {"strref": 282425, "property_name": "m_srParagonPrompt", "value_offset": 144},
            ],
        }
    ]
    rows = _build_semantic_container_usages(semantic_hits)
    assert len(rows) == 1
    assert rows[0]["kind"] == "semantic_container"
    assert rows[0]["source_container"]["parse_mode"] == "stringref_property"
    assert rows[0]["property_name"] == "m_srParagonPrompt"


def test_merge_strref_usages_with_container_fallback_prefers_semantic_container() -> None:
    semantic_rows = [{"kind": "semantic_container", "strref": 999}]
    merged, source = _merge_strref_usages_with_container_fallback([], semantic_rows, [])
    assert source == "semantic_container"
    assert merged == semantic_rows
