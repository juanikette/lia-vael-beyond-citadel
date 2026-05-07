from __future__ import annotations

from pcc_dialog_toolkit.model.ast import Conversation, EntryNode, ReplyNode, Speaker
from pcc_dialog_toolkit.pcc.models import ExportEntry, PccPackage
from pcc_dialog_toolkit.pcc.properties import (
    extract_bioconversation_key_properties,
    read_array_property_count,
    read_array_property_i32_values,
)


def _conversation_counts(package: PccPackage, export: ExportEntry) -> tuple[int, int, int]:
    tags = extract_bioconversation_key_properties(package.raw_data, package.names, export)
    counts = {"EntryList": 0, "ReplyList": 0, "SpeakerList": 0}
    for tag in tags:
        counts[tag.name] = max(0, read_array_property_count(package.raw_data, tag))
    return counts["EntryList"], counts["ReplyList"], counts["SpeakerList"]


def _conversation_arrays(package: PccPackage, export: ExportEntry) -> tuple[list[int], list[int], list[int]]:
    tags = extract_bioconversation_key_properties(package.raw_data, package.names, export)
    mapped = {tag.name: tag for tag in tags}

    entry_values = read_array_property_i32_values(package.raw_data, mapped["EntryList"]) if "EntryList" in mapped else []
    reply_values = read_array_property_i32_values(package.raw_data, mapped["ReplyList"]) if "ReplyList" in mapped else []
    speaker_values = read_array_property_i32_values(package.raw_data, mapped["SpeakerList"]) if "SpeakerList" in mapped else []
    return entry_values, reply_values, speaker_values


def parse_bioconversation_stub(package: PccPackage, export: ExportEntry) -> Conversation:
    entry_count, reply_count, speaker_count = _conversation_counts(package, export)
    entry_values, reply_values, speaker_values = _conversation_arrays(package, export)

    entry_ids = entry_values if len(entry_values) == entry_count else list(range(entry_count))
    reply_targets = reply_values if len(reply_values) == reply_count else [i if i < entry_count else -1 for i in range(reply_count)]
    speaker_ids = speaker_values if len(speaker_values) == speaker_count else list(range(speaker_count))

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
        for i in entry_ids
    ]

    replies = [
        ReplyNode(
            id=i,
            line_strref=None,
            line_text=None,
            target_entry_id=target if target >= 0 else None,
            condition_refs=[],
        )
        for i, target in enumerate(reply_targets)
    ]

    speakers = [
        Speaker(
            id=i,
            tag=None,
            display_name=None,
        )
        for i in speaker_ids
    ]

    links_by_entry: dict[int, list[int]] = {entry.id: [] for entry in entries}
    for reply in replies:
        if reply.target_entry_id is not None and reply.target_entry_id in links_by_entry:
            links_by_entry[reply.target_entry_id].append(reply.id)
    for entry in entries:
        entry.reply_links = links_by_entry.get(entry.id, [])

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
