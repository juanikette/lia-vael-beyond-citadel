from __future__ import annotations

import json
from pathlib import Path

from model.ast import Conversation


SCHEMA_VERSION = "0.1"
TOOL_VERSION = "0.1.0"


def build_output_payload(
    *,
    input_pcc: str,
    game: str | None,
    conversations: list[Conversation],
    errors: list[dict[str, object]],
) -> dict[str, object]:
    warning_count = sum(len(item.warnings) for item in conversations)
    return {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "input": {
            "pcc": input_pcc,
            "game": game,
        },
        "summary": {
            "conversations_total": len(conversations) + len(errors),
            "conversations_ok": len(conversations),
            "conversations_failed": len(errors),
            "warnings_total": warning_count,
        },
        "conversations": [item.to_dict() for item in conversations],
        "errors": errors,
    }


def validate_output_payload(payload: dict[str, object]) -> None:
    required_top = ("schema_version", "tool_version", "input", "summary", "conversations", "errors")
    for key in required_top:
        if key not in payload:
            raise ValueError(f"missing top-level field: {key}")

    summary = payload["summary"]
    if not isinstance(summary, dict):
        raise ValueError("summary must be an object")
    required_summary = (
        "conversations_total",
        "conversations_ok",
        "conversations_failed",
        "warnings_total",
    )
    for key in required_summary:
        if key not in summary:
            raise ValueError(f"missing summary field: {key}")

    conversations = payload["conversations"]
    if not isinstance(conversations, list):
        raise ValueError("conversations must be a list")
    errors = payload["errors"]
    if not isinstance(errors, list):
        raise ValueError("errors must be a list")

    expected_total = int(summary["conversations_ok"]) + int(summary["conversations_failed"])
    if int(summary["conversations_total"]) != expected_total:
        raise ValueError("summary counts are inconsistent")
    if int(summary["conversations_ok"]) != len(conversations):
        raise ValueError("summary conversations_ok does not match payload")
    if int(summary["conversations_failed"]) != len(errors):
        raise ValueError("summary conversations_failed does not match payload")


def write_output_json(
    *,
    output_path: str | Path,
    payload: dict[str, object],
    pretty: bool = False,
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = (
        json.dumps(payload, ensure_ascii=False, indent=2)
        if pretty
        else json.dumps(payload, ensure_ascii=False)
    )
    target.write_text(text + "\n", encoding="utf-8")
    return target
