from __future__ import annotations

from pcc_dialog_toolkit.model.ast import Conversation, EntryNode, ReplyNode, Speaker
from pcc_dialog_toolkit.pcc.models import ExportEntry, PccPackage
from pcc_dialog_toolkit.pcc.reader import _read_i32
from pcc_dialog_toolkit.pcc.properties import (
    analyze_array_property_layout,
    extract_bioconversation_key_properties,
    read_array_property_count,
    read_array_property_i32_rows,
    read_array_property_struct_i32_matrix,
    read_array_property_struct_head_i32,
    read_array_property_i32_values,
    read_array_property_payload_info,
)
from pcc_dialog_toolkit.pcc.unreal_props import parse_struct_array_items_as_property_collections, PROPERTY_TYPE_NAMES
from pcc_dialog_toolkit.dialogue.schema import ConversationListSchema, get_schema_for_profile


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
    schema: ConversationListSchema,
) -> tuple[list[list[int]], list[list[int]], list[list[int]], bool, bool]:
    tags = extract_bioconversation_key_properties(package.raw_data, package.names, export)
    mapped = {tag.name: tag for tag in tags}

    # Bootstrap schema used while full struct parsing is pending:
    # EntryList rows: [id, speaker_id, line_strref]
    # ReplyList rows: [id, target_entry_id, line_strref]
    # SpeakerList rows: [id, tag_name_index, display_name_strref]
    used_struct_head = False
    used_struct_matrix = False

    def _read_rows(key: str, head_i32: int) -> list[list[int]]:
        nonlocal used_struct_head, used_struct_matrix
        tag = mapped.get(key)
        if tag is None:
            return []

        tight_rows = read_array_property_i32_rows(package.raw_data, tag, item_width=head_i32)
        if tight_rows:
            return tight_rows

        matrix_rows = read_array_property_struct_i32_matrix(package.raw_data, tag)
        if matrix_rows and len(matrix_rows[0]) >= head_i32:
            used_struct_matrix = True
            return [row[:head_i32] for row in matrix_rows]

        struct_rows = read_array_property_struct_head_i32(package.raw_data, tag, head_i32=head_i32)
        if struct_rows:
            used_struct_head = True
        return struct_rows

    entry_rows = _read_rows("EntryList", schema.entry_head_i32)
    reply_rows = _read_rows("ReplyList", schema.reply_head_i32)
    speaker_rows = _read_rows("SpeakerList", schema.speaker_head_i32)
    return entry_rows, reply_rows, speaker_rows, used_struct_head, used_struct_matrix


def _row_payload_is_coherent(
    entry_rows: list[list[int]], reply_rows: list[list[int]], speaker_rows: list[list[int]]
) -> bool:
    entry_ids = [row[0] for row in entry_rows if row]
    reply_ids = [row[0] for row in reply_rows if row]
    speaker_ids = [row[0] for row in speaker_rows if row]
    if len(entry_ids) != len(set(entry_ids)):
        return False
    if len(reply_ids) != len(set(reply_ids)):
        return False
    if len(speaker_ids) != len(set(speaker_ids)):
        return False

    known_speakers = set(speaker_ids)
    for row in entry_rows:
        if len(row) > 1 and row[1] >= 0 and row[1] not in known_speakers:
            return False
    return True


def _has_struct_signature(package: PccPackage, *, payload_offset: int, payload_size: int) -> bool:
    if payload_size < 24:
        return False
    end = payload_offset + payload_size
    if payload_offset < 0 or end > len(package.raw_data):
        return False

    a = _read_i32(package.raw_data, payload_offset)
    b = _read_i32(package.raw_data, payload_offset + 4)
    ta = _read_i32(package.raw_data, payload_offset + 8)
    tb = _read_i32(package.raw_data, payload_offset + 12)

    a_ok = 0 <= a < len(package.names)
    b_ok = 0 <= b < len(package.names)
    if not (a_ok or b_ok):
        return False

    ta_name = package.names[ta].text if 0 <= ta < len(package.names) else None
    tb_name = package.names[tb].text if 0 <= tb < len(package.names) else None
    return (ta_name in PROPERTY_TYPE_NAMES) or (tb_name in PROPERTY_TYPE_NAMES)


def _try_semantic_struct_nodes(
    package: PccPackage,
    tag_map: dict[str, object],
) -> tuple[list[EntryNode], list[ReplyNode], list[Speaker]] | None:
    if "EntryList" not in tag_map:
        return None

    entry_count, entry_payload, entry_payload_size = read_array_property_payload_info(package.raw_data, tag_map["EntryList"])
    if entry_count <= 0 or entry_payload_size <= 0:
        return None
    if not _has_struct_signature(package, payload_offset=entry_payload, payload_size=entry_payload_size):
        return None

    try:
        entry_items = parse_struct_array_items_as_property_collections(
            package.raw_data,
            package.names,
            payload_offset=entry_payload,
            payload_size=entry_payload_size,
            count=entry_count,
        )
        reply_items = []
        if "ReplyList" in tag_map:
            reply_count, reply_payload, reply_payload_size = read_array_property_payload_info(package.raw_data, tag_map["ReplyList"])
            reply_items = parse_struct_array_items_as_property_collections(
                package.raw_data,
                package.names,
                payload_offset=reply_payload,
                payload_size=reply_payload_size,
                count=max(0, reply_count),
            )
    except Exception:
        return None

    if not entry_items:
        return None

    entries: list[EntryNode] = []
    for idx, item in enumerate(entry_items):
        sr_text = item.get("srText")
        spk = item.get("nSpeakerIndex")
        speaker_id = int(spk.value) if spk and isinstance(spk.value, int) and spk.value >= 0 else None
        entries.append(
            EntryNode(
                id=idx,
                speaker_id=speaker_id,
                speaker_tag=None,
                listener_tag=None,
                line_strref=int(sr_text.value) if sr_text and isinstance(sr_text.value, int) else None,
                line_text=None,
                reply_links=[],
            )
        )

    replies: list[ReplyNode] = []
    for idx, item in enumerate(reply_items):
        sr_text = item.get("srText")
        target = item.get("nIndex") or item.get("nEntryIndex")
        cond_func = item.get("nConditionalFunc")
        cond_param = item.get("nConditionalParam")
        refs: list[str] = []
        if cond_func and isinstance(cond_func.value, int) and cond_func.value >= 0:
            refs.append(f"cond_func:{cond_func.value}")
        if cond_param and isinstance(cond_param.value, int) and cond_param.value != 0:
            refs.append(f"cond_param:{cond_param.value}")
        replies.append(
            ReplyNode(
                id=idx,
                line_strref=int(sr_text.value) if sr_text and isinstance(sr_text.value, int) else None,
                line_text=None,
                target_entry_id=int(target.value) if target and isinstance(target.value, int) else None,
                condition_refs=refs,
            )
        )

    speakers: list[Speaker] = []
    if "SpeakerList" in tag_map:
        spk_count, spk_payload, spk_payload_size = read_array_property_payload_info(package.raw_data, tag_map["SpeakerList"])
        if spk_count > 0 and spk_payload_size > 0 and _has_struct_signature(package, payload_offset=spk_payload, payload_size=spk_payload_size):
            try:
                speaker_items = parse_struct_array_items_as_property_collections(
                    package.raw_data,
                    package.names,
                    payload_offset=spk_payload,
                    payload_size=spk_payload_size,
                    count=spk_count,
                )
                for idx, item in enumerate(speaker_items):
                    tag_prop = item.get("sSpeakerTag")
                    speakers.append(
                        Speaker(
                            id=idx,
                            tag=str(tag_prop.value) if tag_prop and isinstance(tag_prop.value, str) else None,
                            display_name=None,
                        )
                    )
            except Exception:
                speakers = []

    return entries, replies, speakers


def parse_bioconversation_stub(package: PccPackage, export: ExportEntry) -> Conversation:
    game_profile = package.infer_game_profile()
    schema = get_schema_for_profile(game_profile)
    entry_count, reply_count, speaker_count = _conversation_counts(package, export)
    entry_values, reply_values, speaker_values = _conversation_arrays(package, export)
    entry_rows, reply_rows, speaker_rows, used_struct_head, used_struct_matrix = _conversation_row_arrays(
        package,
        export,
        schema,
    )
    row_mode = bool(entry_rows and reply_rows and speaker_rows)
    row_payload_rejected = False
    if row_mode and not _row_payload_is_coherent(entry_rows, reply_rows, speaker_rows):
        row_mode = False
        row_payload_rejected = True
        used_struct_head = False
        used_struct_matrix = False
    warnings: list[str] = []
    if entry_count == 0 and reply_count == 0 and speaker_count == 0:
        warnings.append("empty_key_arrays")
    tags = extract_bioconversation_key_properties(package.raw_data, package.names, export)
    tag_map = {tag.name: tag for tag in tags}
    semantic_mode = False
    semantic_nodes = _try_semantic_struct_nodes(package, tag_map)
    if semantic_nodes is not None:
        semantic_mode = True

    missing_keys = [key for key in ("EntryList", "ReplyList", "SpeakerList") if key not in tag_map]
    if missing_keys and not semantic_mode:
        warnings.append(f"missing_key_properties:{','.join(missing_keys)}")
    entry_matrix = read_array_property_struct_i32_matrix(package.raw_data, tag_map["EntryList"]) if "EntryList" in tag_map else []
    reply_matrix = read_array_property_struct_i32_matrix(package.raw_data, tag_map["ReplyList"]) if "ReplyList" in tag_map else []
    speaker_matrix = read_array_property_struct_i32_matrix(package.raw_data, tag_map["SpeakerList"]) if "SpeakerList" in tag_map else []
    if game_profile == "unknown":
        warnings.append("unknown_game_profile")
    for key in ("EntryList", "ReplyList", "SpeakerList"):
        tag = tag_map.get(key)
        if tag is None:
            continue
        layout = analyze_array_property_layout(package.raw_data, tag)
        if not layout.is_tight_i32 and layout.count > 0 and not semantic_mode and not (used_struct_head or used_struct_matrix):
            warnings.append(
                f"non_tight_i32_array:{key}:count={layout.count}:bytes_per_item={layout.bytes_per_item}:remainder={layout.remainder}"
            )

    entry_ids = entry_values if len(entry_values) == entry_count else list(range(entry_count))
    reply_targets = reply_values if len(reply_values) == reply_count else [i if i < entry_count else -1 for i in range(reply_count)]
    speaker_ids = speaker_values if len(speaker_values) == speaker_count else list(range(speaker_count))

    if semantic_mode and semantic_nodes is not None:
        entries, replies, speakers = semantic_nodes
    elif row_mode:
        entries = []
        for idx, row in enumerate(entry_rows):
            listener_tag = None
            if (
                used_struct_matrix
                and schema.entry_listener_tag_name_idx_col is not None
                and idx < len(entry_matrix)
                and len(entry_matrix[idx]) > schema.entry_listener_tag_name_idx_col
            ):
                name_idx = entry_matrix[idx][schema.entry_listener_tag_name_idx_col]
                if 0 <= name_idx < len(package.names):
                    listener_tag = package.names[name_idx].text
            entries.append(
                EntryNode(
                    id=row[0],
                    speaker_id=row[1] if row[1] >= 0 else None,
                    speaker_tag=None,
                    listener_tag=listener_tag,
                    line_strref=row[2] if row[2] >= 0 else None,
                    line_text=None,
                    reply_links=[],
                )
            )
    else:
        if row_payload_rejected:
            warnings.append("row_payload_incoherent_fallback_applied")
        elif entry_rows or reply_rows or speaker_rows:
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

    if semantic_mode:
        pass
    elif row_mode:
        replies = []
        for idx, row in enumerate(reply_rows):
            condition_refs: list[str] = []
            if (
                used_struct_matrix
                and schema.reply_condition_start_col is not None
                and idx < len(reply_matrix)
                and len(reply_matrix[idx]) > schema.reply_condition_start_col
            ):
                for value in reply_matrix[idx][schema.reply_condition_start_col :]:
                    if value >= 0:
                        condition_refs.append(f"cond_i32:{value}")
            replies.append(
                ReplyNode(
                    id=row[0],
                    line_strref=row[2] if row[2] >= 0 else None,
                    line_text=None,
                    target_entry_id=row[1] if row[1] >= 0 else None,
                    condition_refs=condition_refs,
                )
            )
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

    if semantic_mode:
        pass
    elif row_mode:
        speakers = []
        for idx, row in enumerate(speaker_rows):
            display_name = None
            if (
                used_struct_matrix
                and schema.speaker_display_name_strref_col is not None
                and idx < len(speaker_matrix)
                and len(speaker_matrix[idx]) > schema.speaker_display_name_strref_col
            ):
                strref = speaker_matrix[idx][schema.speaker_display_name_strref_col]
                if strref >= 0:
                    display_name = f"strref:{strref}"
            speakers.append(
                Speaker(
                    id=row[0],
                    tag=package.names[row[1]].text if 0 <= row[1] < len(package.names) else None,
                    display_name=display_name,
                )
            )
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
        game_profile=game_profile,
        entries=entries,
        replies=replies,
        speakers=speakers,
        parse_mode=(
            "struct_property_semantic"
            if semantic_mode
            else (
                "row_payload_struct_matrix"
                if (row_mode and used_struct_matrix)
                else (
                    "row_payload_struct_head"
                    if (row_mode and used_struct_head)
                    else ("row_payload" if row_mode else "count_or_value_fallback")
                )
            )
        ),
        warnings=warnings,
    )


def _has_bioconversation_serial_data(export: ExportEntry) -> bool:
    return export.serial_size >= 8 and export.serial_offset > 0


def parse_all_bioconversation_stubs(package: PccPackage) -> list[Conversation]:
    rows: list[Conversation] = []
    for export in package.iter_exports(class_name="BioConversation"):
        if not _has_bioconversation_serial_data(export):
            continue
        rows.append(parse_bioconversation_stub(package, export))
    return rows


def parse_all_bioconversation_stubs_resilient(
    package: PccPackage,
) -> tuple[list[Conversation], list[dict[str, object]]]:
    rows: list[Conversation] = []
    errors: list[dict[str, object]] = []
    for export in package.iter_exports(class_name="BioConversation"):
        if not _has_bioconversation_serial_data(export):
            continue
        try:
            rows.append(parse_bioconversation_stub(package, export))
        except Exception as exc:
            errors.append(
                {
                    "id": export.object_name or f"Export_{export.index}",
                    "export_index": export.index,
                    "error": f"{exc.__class__.__name__}: {exc}",
                }
            )
    return rows, errors


def validate_bioconversation_stub(stub: Conversation) -> list[str]:
    issues: list[str] = []

    entry_ids = {entry.id for entry in stub.entries}
    reply_ids = {reply.id for reply in stub.replies}
    speaker_ids = {speaker.id for speaker in stub.speakers}

    if len(entry_ids) != len(stub.entries):
        issues.append("duplicate_entry_ids")
    if len(reply_ids) != len(stub.replies):
        issues.append("duplicate_reply_ids")
    if len(speaker_ids) != len(stub.speakers):
        issues.append("duplicate_speaker_ids")

    for entry in stub.entries:
        if entry.speaker_id is not None and entry.speaker_id not in speaker_ids:
            issues.append(f"entry_speaker_missing:{entry.id}->{entry.speaker_id}")
        for reply_id in entry.reply_links:
            if reply_id not in reply_ids:
                issues.append(f"entry_reply_link_missing:{entry.id}->{reply_id}")

    for reply in stub.replies:
        if reply.target_entry_id is not None and reply.target_entry_id not in entry_ids:
            issues.append(f"reply_target_missing:{reply.id}->{reply.target_entry_id}")

    return sorted(set(issues))


def validate_all_bioconversation_stubs(package: PccPackage) -> list[dict[str, object]]:
    reports: list[dict[str, object]] = []
    for stub in parse_all_bioconversation_stubs(package):
        issues = validate_bioconversation_stub(stub)
        needs_schema_review = (
            stub.game_profile == "unknown"
            or any(w.startswith("non_tight_i32_array:") for w in stub.warnings)
            or (stub.parse_mode == "count_or_value_fallback" and len(stub.warnings) > 0)
        )
        reports.append(
            {
                "id": stub.id,
                "export_index": stub.export_index,
                "game_profile": stub.game_profile,
                "parse_mode": stub.parse_mode,
                "warnings": stub.warnings,
                "issues": issues,
                "is_valid": len(issues) == 0,
                "needs_schema_review": needs_schema_review,
            }
        )
    return reports


def summarize_stub_validation(reports: list[dict[str, object]]) -> dict[str, object]:
    total = len(reports)
    valid = sum(1 for row in reports if bool(row.get("is_valid")))
    needs_review = sum(1 for row in reports if bool(row.get("needs_schema_review")))
    invalid = total - valid

    by_parse_mode: dict[str, int] = {}
    for row in reports:
        mode = str(row.get("parse_mode", "unknown"))
        by_parse_mode[mode] = by_parse_mode.get(mode, 0) + 1

    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "needs_schema_review": needs_review,
        "by_parse_mode": by_parse_mode,
    }


def inspect_bioconversation_row_payloads(package: PccPackage) -> list[dict[str, object]]:
    report: list[dict[str, object]] = []
    for export in package.iter_exports(class_name="BioConversation"):
        if not _has_bioconversation_serial_data(export):
            continue
        profile = package.infer_game_profile()
        schema = get_schema_for_profile(profile)
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

        entry_rows, reply_rows, speaker_rows, used_struct_head, used_struct_matrix = _conversation_row_arrays(
            package,
            export,
            schema,
        )
        report.append(
            {
                "id": export.object_name or f"Export_{export.index}",
                "export_index": export.index,
                "game_profile": profile,
                "schema": {
                    "entry_head_i32": schema.entry_head_i32,
                    "reply_head_i32": schema.reply_head_i32,
                    "speaker_head_i32": schema.speaker_head_i32,
                    "entry_listener_tag_name_idx_col": schema.entry_listener_tag_name_idx_col,
                    "reply_condition_start_col": schema.reply_condition_start_col,
                    "speaker_display_name_strref_col": schema.speaker_display_name_strref_col,
                },
                "array_layouts": layouts,
                "entry_rows": entry_rows,
                "reply_rows": reply_rows,
                "speaker_rows": speaker_rows,
                "row_payload_complete": bool(entry_rows and reply_rows and speaker_rows),
                "used_struct_head": used_struct_head,
                "used_struct_matrix": used_struct_matrix,
            }
        )
    return report
