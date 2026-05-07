from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class EntryNode:
    id: int
    speaker_id: int | None
    speaker_tag: str | None
    listener_tag: str | None
    line_strref: int | None
    line_text: str | None
    reply_links: list[int]


@dataclass(slots=True)
class ReplyNode:
    id: int
    line_strref: int | None
    line_text: str | None
    target_entry_id: int | None
    condition_refs: list[str]


@dataclass(slots=True)
class Speaker:
    id: int
    tag: str | None
    display_name: str | None


@dataclass(slots=True)
class Conversation:
    id: str
    export_index: int
    package_path: str
    entries: list[EntryNode]
    replies: list[ReplyNode]
    speakers: list[Speaker]
    parse_mode: str
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
