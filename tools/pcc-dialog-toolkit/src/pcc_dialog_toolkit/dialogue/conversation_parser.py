from __future__ import annotations

from pcc_dialog_toolkit.model.ast import Conversation, EntryNode, ReplyNode, Speaker
from pcc_dialog_toolkit.pcc.models import ExportEntry, PccPackage
from pcc_dialog_toolkit.pcc.properties import extract_bioconversation_key_properties, read_array_property_count


def _conversation_counts(package: PccPackage, export: ExportEntry) -> tuple[int, int, int]:
    tags = extract_bioconversation_key_properties(package.raw_data, package.names, export)
    counts = {"EntryList": 0, "ReplyList": 0, "SpeakerList": 0}
    for tag in tags:
        counts[tag.name] = max(0, read_array_property_count(package.raw_data, tag))
    return counts["EntryList"], counts["ReplyList"], counts["SpeakerList"]


def parse_bioconversation_stub(package: PccPackage, export: ExportEntry) -> Conversation:
    entry_count, reply_count, speaker_count = _conversation_counts(package, export)

    entries = [
        EntryNode(
            id=i,
            speaker_id=None,
            speaker_tag=None,
            listener_tag=None,
            line_strref=None,
            line_text=None,
            reply_links=[],
        )
        for i in range(entry_count)
    ]

    replies = [
        ReplyNode(
            id=i,
            line_strref=None,
            line_text=None,
            target_entry_id=i if i < entry_count else None,
            condition_refs=[],
        )
        for i in range(reply_count)
    ]

    speakers = [
        Speaker(
            id=i,
            tag=None,
            display_name=None,
        )
        for i in range(speaker_count)
    ]

    return Conversation(
        id=export.object_name or f"Export_{export.index}",
        export_index=export.index,
        package_path=package.path,
        entries=entries,
        replies=replies,
        speakers=speakers,
    )


def parse_all_bioconversation_stubs(package: PccPackage) -> list[Conversation]:
    rows: list[Conversation] = []
    for export in package.iter_exports(class_name="BioConversation"):
        rows.append(parse_bioconversation_stub(package, export))
    return rows
