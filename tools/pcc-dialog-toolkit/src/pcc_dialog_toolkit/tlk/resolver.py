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


def find_dlc_tlk_files(dlc_dir: str | Path, *, language: str = "INT") -> list[Path]:
    root = Path(dlc_dir)
    if not root.exists() or not root.is_dir():
        return []
    scored: list[tuple[int, str, Path]] = []
    for candidate in root.glob("**/*.tlk"):
        if not candidate.is_file() or not candidate.name.upper().endswith(f"_{language}.TLK"):
            continue
        try:
            rel = candidate.relative_to(root)
        except ValueError:
            rel = candidate
        dlc_folder = rel.parts[0] if rel.parts else ""
        mount = _read_mount_priority(root / dlc_folder) if dlc_folder else 0
        scored.append((mount, str(rel).lower(), candidate))
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
) -> TlkResolver:
    files: list[TlkFile] = []
    if dlc_dir is not None:
        for dlc_tlk in find_dlc_tlk_files(dlc_dir, language=language):
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
