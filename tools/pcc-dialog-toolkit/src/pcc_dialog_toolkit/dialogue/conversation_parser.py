from __future__ import annotations

from pcc_dialog_toolkit.model.ast import Conversation, EntryNode, ReplyNode, Speaker
from pcc_dialog_toolkit.pcc.models import ExportEntry, PccPackage
from pcc_dialog_toolkit.pcc.properties import (
    analyze_array_property_layout,
    extract_bioconversation_key_properties,
    read_array_property_count,
    read_array_property_i32_rows,
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


def _conversation_row_arrays(
    package: PccPackage,
    export: ExportEntry,
) -> tuple[list[list[int]], list[list[int]], list[list[int]]]:
    tags = extract_bioconversation_key_properties(package.raw_data, package.names, export)
    mapped = {tag.name: tag for tag in tags}

    # Bootstrap schema used while full struct parsing is pending:
    # EntryList rows: [id, speaker_id, line_strref]
    # ReplyList rows: [id, target_entry_id, line_strref]
    # SpeakerList rows: [id, tag_name_index, display_name_strref]
    entry_rows = read_array_property_i32_rows(package.raw_data, mapped["EntryList"], item_width=3) if "EntryList" in mapped else []
    reply_rows = read_array_property_i32_rows(package.raw_data, mapped["ReplyList"], item_width=3) if "ReplyList" in mapped else []
    speaker_rows = read_array_property_i32_rows(package.raw_data, mapped["SpeakerList"], item_width=3) if "SpeakerList" in mapped else []
    return entry_rows, reply_rows, speaker_rows


def parse_bioconversation_stub(package: PccPackage, export: ExportEntry) -> Conversation:
    entry_count, reply_count, speaker_count = _conversation_counts(package, export)
    entry_values, reply_values, speaker_values = _conversation_arrays(package, export)
    entry_rows, reply_rows, speaker_rows = _conversation_row_arrays(package, export)
    row_mode = bool(entry_rows and reply_rows and speaker_rows)
    warnings: list[str] = []
    tags = extract_bioconversation_key_properties(package.raw_data, package.names, export)
    tag_map = {tag.name: tag for tag in tags}
    for key in ("EntryList", "ReplyList", "SpeakerList"):
        tag = tag_map.get(key)
        if tag is None:
            continue
        layout = analyze_array_property_layout(package.raw_data, tag)
        if not layout.is_tight_i32 and layout.count > 0:
            warnings.append(
                f"non_tight_i32_array:{key}:count={layout.count}:bytes_per_item={layout.bytes_per_item}:remainder={layout.remainder}"
            )

    entry_ids = entry_values if len(entry_values) == entry_count else list(range(entry_count))
    reply_targets = reply_values if len(reply_values) == reply_count else [i if i < entry_count else -1 for i in range(reply_count)]
    speaker_ids = speaker_values if len(speaker_values) == speaker_count else list(range(speaker_count))

    if row_mode:
        entries = [
            EntryNode(
                id=row[0],
                speaker_id=row[1] if row[1] >= 0 else None,
                speaker_tag=None,
                listener_tag=None,
                line_strref=row[2] if row[2] >= 0 else None,
                line_text=None,
                reply_links=[],
            )
            for row in entry_rows
        ]
    else:
        if entry_rows or reply_rows or speaker_rows:
            warnings.append("partial_row_payload_detected_fallback_applied")
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

    if row_mode:
        replies = [
            ReplyNode(
                id=row[0],
                line_strref=row[2] if row[2] >= 0 else None,
                line_text=None,
                target_entry_id=row[1] if row[1] >= 0 else None,
                condition_refs=[],
            )
            for row in reply_rows
        ]
    else:
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

    if row_mode:
        speakers = [
            Speaker(
                id=row[0],
                tag=package.names[row[1]].text if 0 <= row[1] < len(package.names) else None,
                display_name=None,
            )
            for row in speaker_rows
        ]
    else:
        speakers = [
            Speaker(
                id=i,
                tag=None,
                display_name=None,
            )
            for i in speaker_ids
        ]

    links_by_entry: dict[int, list[int]] = {entry.id: [] for entry in entries}
    known_entry_ids = set(links_by_entry)
    for reply in replies:
        if reply.target_entry_id is None:
            continue
        if reply.target_entry_id in known_entry_ids:
            links_by_entry[reply.target_entry_id].append(reply.id)
        else:
            warnings.append(f"reply_target_missing_entry:{reply.id}->{reply.target_entry_id}")
    for entry in entries:
        entry.reply_links = links_by_entry.get(entry.id, [])

    return Conversation(
        id=export.object_name or f"Export_{export.index}",
        export_index=export.index,
        package_path=package.path,
        entries=entries,
        replies=replies,
        speakers=speakers,
        parse_mode="row_payload" if row_mode else "count_or_value_fallback",
        warnings=warnings,
    )


def parse_all_bioconversation_stubs(package: PccPackage) -> list[Conversation]:
    rows: list[Conversation] = []
    for export in package.iter_exports(class_name="BioConversation"):
        rows.append(parse_bioconversation_stub(package, export))
    return rows


def inspect_bioconversation_row_payloads(package: PccPackage) -> list[dict[str, object]]:
    report: list[dict[str, object]] = []
    for export in package.iter_exports(class_name="BioConversation"):
        tags = extract_bioconversation_key_properties(package.raw_data, package.names, export)
        tag_map = {tag.name: tag for tag in tags}

        layouts: dict[str, dict[str, int | bool | None]] = {}
        for key in ("EntryList", "ReplyList", "SpeakerList"):
            if key not in tag_map:
                continue
            info = analyze_array_property_layout(package.raw_data, tag_map[key])
            layouts[key] = {
                "count": info.count,
                "payload_size": info.payload_size,
                "bytes_per_item": info.bytes_per_item,
                "remainder": info.remainder,
                "is_tight_i32": info.is_tight_i32,
            }

        entry_rows, reply_rows, speaker_rows = _conversation_row_arrays(package, export)
        report.append(
            {
                "id": export.object_name or f"Export_{export.index}",
                "export_index": export.index,
                "array_layouts": layouts,
                "entry_rows": entry_rows,
                "reply_rows": reply_rows,
                "speaker_rows": speaker_rows,
                "row_payload_complete": bool(entry_rows and reply_rows and speaker_rows),
            }
        )
    return report
