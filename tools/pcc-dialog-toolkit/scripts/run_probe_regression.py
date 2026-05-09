from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run_probe(out_path: Path, queries: list[str], tlk: Path, dlc_dir: Path) -> dict[str, object]:
    cmd = [
        sys.executable,
        "-m",
        "cli",
        "--evidence-report",
        str(out_path),
        "--tlk",
        str(tlk),
        "--dlc-dir",
        str(dlc_dir),
        "--pretty",
    ]
    for query in queries:
        cmd.extend(["--evidence-query", query])

    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"probe command failed ({out_path.name}): {completed.stderr.strip()}")

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    return payload


def _assert_probe_basics(name: str, payload: dict[str, object]) -> list[str]:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return [f"{name}: missing summary"]

    errors: list[str] = []
    if int(summary.get("tlk_hits", 0)) <= 0:
        errors.append(f"{name}: tlk_hits <= 0")
    if int(summary.get("raw_export_hits", 0)) <= 0:
        errors.append(f"{name}: raw_export_hits <= 0")
    if int(summary.get("candidate_pcc_files", 0)) <= 0:
        errors.append(f"{name}: candidate_pcc_files <= 0")
    if payload.get("evidence_schema_version") != "1.0.0":
        errors.append(f"{name}: evidence_schema_version != 1.0.0")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 12 narrative probe regression harness.")
    parser.add_argument("--tlk", required=True, help="Path to BIOGame_INT.tlk")
    parser.add_argument("--dlc-dir", required=True, help="Path to BioGame/DLC")
    parser.add_argument("--out-dir", default="reports", help="Output directory for probe reports")
    args = parser.parse_args()

    tlk = Path(args.tlk)
    dlc_dir = Path(args.dlc_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    probes = {
        "tali_intimacy": [
            "dalliance attractive as stress release",
            "self-sterilize",
            "oral contact with tissue dangerous",
        ],
        "miss_vas_normandy": ["miss vas normandy"],
        "rally_the_crowd": ["rally the crowd"],
    }

    payloads: dict[str, dict[str, object]] = {}
    for name, queries in probes.items():
        out_path = out_dir / f"probe_{name}.json"
        payloads[name] = _run_probe(out_path, queries, tlk, dlc_dir)

    failures: list[str] = []
    for name, payload in payloads.items():
        failures.extend(_assert_probe_basics(name, payload))

    semantic_probe_count = 0
    for payload in payloads.values():
        summary = payload.get("summary")
        if not isinstance(summary, dict):
            continue
        if summary.get("strref_usage_source") == "semantic_container":
            semantic_probe_count += 1
    if semantic_probe_count < 1:
        failures.append("semantic gate: expected at least one probe with strref_usage_source=semantic_container")

    print("Probe regression summary:")
    for name, payload in payloads.items():
        summary = payload.get("summary", {})
        print(
            f"- {name}: source={summary.get('strref_usage_source')} "
            f"semantic={summary.get('semantic_container_usages')} tlk={summary.get('tlk_hits')} "
            f"raw={summary.get('raw_export_hits')} total_ms={summary.get('timing_ms', {}).get('total')}"
        )

    if failures:
        print("\nRegression FAILED:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("\nRegression PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
