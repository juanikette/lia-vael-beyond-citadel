from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from pcc_dialog_toolkit.model.ast import Conversation

from .reader import TlkFile, read_tlk, resolve_tlk_string


def _read_mount_priority(dlc_root: Path) -> int:
    mount_file = dlc_root / "Mount.dlc"
    if not mount_file.exists() or not mount_file.is_file():
        return 0
    try:
        content = mount_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    match = re.search(r"(?im)^\s*MountPriority\s*=\s*(\d+)\s*$", content)
    if not match:
        return 0
    return int(match.group(1))


def find_dlc_tlk_files(
    dlc_dir: str | Path,
    *,
    language: str = "INT",
    include_test_tlks: bool = False,
) -> list[Path]:
    root = Path(dlc_dir)
    if not root.exists() or not root.is_dir():
        return []

    lang_suffix = f"_{language.upper()}.TLK"
    scored: list[tuple[int, str, Path]] = []

    dlc_roots = [
        path
        for path in root.iterdir()
        if path.is_dir() and path.name.upper().startswith("DLC_")
    ]

    def _collect_tlks(base_dir: Path, mount: int, dlc_name: str) -> None:
        for candidate in base_dir.rglob("*.tlk"):
            if not candidate.is_file() or not candidate.name.upper().endswith(lang_suffix):
                continue
            if not include_test_tlks and candidate.stem.upper().endswith("_TEST_INT"):
                continue
            rel = candidate.relative_to(root)
            scored.append((mount, f"{dlc_name.lower()}::{str(rel).lower()}", candidate))

    for dlc_root in dlc_roots:
        mount = _read_mount_priority(dlc_root)
        cooked_dirs = [
            child
            for child in dlc_root.iterdir()
            if child.is_dir() and child.name.upper().startswith("COOKEDPC")
        ]
        if cooked_dirs:
            for cooked_dir in cooked_dirs:
                _collect_tlks(cooked_dir, mount, dlc_root.name)
        else:
            _collect_tlks(dlc_root, mount, dlc_root.name)

    if not scored:
        for candidate in root.rglob("*.tlk"):
            if not candidate.is_file() or not candidate.name.upper().endswith(lang_suffix):
                continue
            if not include_test_tlks and candidate.stem.upper().endswith("_TEST_INT"):
                continue
            rel = candidate.relative_to(root)
            scored.append((0, str(rel).lower(), candidate))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in scored]


class TlkResolver:
    def __init__(self, files: list[TlkFile]) -> None:
        self._files = files

    def resolve(self, string_id: int | None) -> str | None:
        if string_id is None or string_id < 0:
            return None
        for tlk in self._files:
            value = resolve_tlk_string(tlk, string_id, male=True)
            if value is not None:
                return value
        return None


def build_tlk_resolver(
    *,
    base_tlk_path: str | Path,
    dlc_dir: str | Path | None = None,
    language: str = "INT",
    include_test_tlks: bool = False,
) -> TlkResolver:
    files: list[TlkFile] = []
    if dlc_dir is not None:
        for dlc_tlk in find_dlc_tlk_files(
            dlc_dir,
            language=language,
            include_test_tlks=include_test_tlks,
        ):
            files.append(read_tlk(dlc_tlk))
    files.append(read_tlk(base_tlk_path))
    return TlkResolver(files)


def resolve_conversations_tlk(
    conversations: list[Conversation],
    resolver: TlkResolver,
) -> list[Conversation]:
    resolved: list[Conversation] = []
    for conversation in conversations:
        entries = [
            replace(entry, line_text=resolver.resolve(entry.line_strref))
            for entry in conversation.entries
        ]
        replies = [
            replace(reply, line_text=resolver.resolve(reply.line_strref))
            for reply in conversation.replies
        ]
        resolved.append(replace(conversation, entries=entries, replies=replies))
    return resolved
