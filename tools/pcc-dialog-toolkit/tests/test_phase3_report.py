from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pcc_dialog_toolkit.validation import build_phase3_report, write_phase3_report
from tests.test_phase3_ast_stub import _build_pcc_with_bioconv_row_payloads


def test_phase3_build_report_structure(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_report.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads())

    report = build_phase3_report(pcc_path)
    assert report["game_profile"] == "me2_ot"
    assert "summary" in report
    assert "validation_items" in report
    assert "row_payloads" in report


def test_phase3_write_report_file(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_report.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads())
    out = tmp_path / "reports" / "phase3.json"

    written = write_phase3_report(pcc_path, out, pretty=True)
    assert written.exists()
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["summary"]["total"] == 1


def test_phase3_cli_writes_report_file(tmp_path: Path) -> None:
    pcc_path = tmp_path / "sample_report.pcc"
    pcc_path.write_bytes(_build_pcc_with_bioconv_row_payloads())
    out = tmp_path / "phase3-cli.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pcc_dialog_toolkit",
            str(pcc_path),
            "--phase3-report",
            str(out),
            "--pretty",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["summary"]["total"] == 1
