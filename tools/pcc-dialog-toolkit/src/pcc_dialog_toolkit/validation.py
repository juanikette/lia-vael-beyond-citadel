from __future__ import annotations

import json
from pathlib import Path

from pcc_dialog_toolkit.pcc import read_pcc


def build_phase3_report(pcc_path: str | Path) -> dict[str, object]:
    package = read_pcc(pcc_path)
    validation_items = package.validate_bioconversation_stubs()
    summary = package.summarize_bioconversation_validation()
    row_payloads = package.inspect_bioconversation_row_payloads()

    return {
        "pcc_path": str(pcc_path),
        "game_profile": package.infer_game_profile(),
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
