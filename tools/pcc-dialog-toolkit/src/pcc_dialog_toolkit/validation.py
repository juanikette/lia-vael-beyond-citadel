from __future__ import annotations

import json
from pathlib import Path

from pcc_dialog_toolkit.pcc import PccFormatError, read_pcc


def build_phase3_report(pcc_path: str | Path) -> dict[str, object]:
    try:
        package = read_pcc(pcc_path)
    except (PccFormatError, OSError) as exc:
        return {
            "pcc_path": str(pcc_path),
            "game_profile": "unknown",
            "parse_error": str(exc),
            "summary": {
                "total": 0,
                "valid": 0,
                "invalid": 0,
                "needs_schema_review": 1,
                "by_parse_mode": {},
            },
            "validation_items": [],
            "row_payloads": [],
        }

    try:
        validation_items = package.validate_bioconversation_stubs()
        summary = package.summarize_bioconversation_validation()
        row_payloads = package.inspect_bioconversation_row_payloads()
        parse_error = None
    except (PccFormatError, OSError) as exc:
        validation_items = []
        summary = {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "needs_schema_review": 1,
            "by_parse_mode": {},
        }
        row_payloads = []
        parse_error = str(exc)

    return {
        "pcc_path": str(pcc_path),
        "game_profile": package.infer_game_profile(),
        "parse_error": parse_error,
        "summary": summary,
        "validation_items": validation_items,
        "row_payloads": row_payloads,
    }


def write_phase3_report(pcc_path: str | Path, output_path: str | Path, *, pretty: bool) -> Path:
    report = build_phase3_report(pcc_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2 if pretty else None, ensure_ascii=False)
    out.write_text(text + "\n", encoding="utf-8")
    return out


def build_phase3_batch_report(pcc_paths: list[str | Path]) -> dict[str, object]:
    items: list[dict[str, object]] = []
    totals = {
        "files": 0,
        "conversations": 0,
        "valid": 0,
        "invalid": 0,
        "needs_schema_review": 0,
        "parse_errors": 0,
    }

    for pcc_path in pcc_paths:
        report = build_phase3_report(pcc_path)
        summary = report.get("summary", {})
        totals["files"] += 1
        totals["conversations"] += int(summary.get("total", 0))
        totals["valid"] += int(summary.get("valid", 0))
        totals["invalid"] += int(summary.get("invalid", 0))
        totals["needs_schema_review"] += int(summary.get("needs_schema_review", 0))
        if report.get("parse_error"):
            totals["parse_errors"] += 1
        items.append(report)

    return {
        "summary": totals,
        "items": items,
    }


def write_phase3_batch_report(pcc_paths: list[str | Path], output_path: str | Path, *, pretty: bool) -> Path:
    report = build_phase3_batch_report(pcc_paths)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2 if pretty else None, ensure_ascii=False)
    out.write_text(text + "\n", encoding="utf-8")
    return out
