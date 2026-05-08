from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from validation import build_phase3_batch_report, write_phase3_batch_report
from tests.test_phase3_ast_stub import _build_pcc_with_bioconv_row_payloads


def test_phase3_build_batch_report(tmp_path: Path) -> None:
    pcc_a = tmp_path / "a.pcc"
    pcc_b = tmp_path / "b.pcc"
    pcc_a.write_bytes(_build_pcc_with_bioconv_row_payloads())
    pcc_b.write_bytes(_build_pcc_with_bioconv_row_payloads())

    report = build_phase3_batch_report([pcc_a, pcc_b])
    assert report["summary"]["files"] == 2
    assert report["summary"]["conversations"] == 2
    assert len(report["items"]) == 2


def test_phase3_write_batch_report(tmp_path: Path) -> None:
    pcc_a = tmp_path / "a.pcc"
    pcc_a.write_bytes(_build_pcc_with_bioconv_row_payloads())
    out = tmp_path / "reports" / "batch.json"

    written = write_phase3_batch_report([pcc_a], out, pretty=True)
    assert written.exists()
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["summary"]["files"] == 1


def test_phase3_cli_batch_report(tmp_path: Path) -> None:
    pcc_a = tmp_path / "a.pcc"
    pcc_b = tmp_path / "b.pcc"
    pcc_a.write_bytes(_build_pcc_with_bioconv_row_payloads())
    pcc_b.write_bytes(_build_pcc_with_bioconv_row_payloads())
    out = tmp_path / "batch-cli.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli",
            "--phase3-batch-dir",
            str(tmp_path),
            "--phase3-batch-glob",
            "*.pcc",
            "--phase3-batch-report",
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
    assert payload["summary"]["files"] == 2
