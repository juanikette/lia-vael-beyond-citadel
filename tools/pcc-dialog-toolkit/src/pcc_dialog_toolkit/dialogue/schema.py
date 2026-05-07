from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConversationListSchema:
    entry_head_i32: int
    reply_head_i32: int
    speaker_head_i32: int


SCHEMA_BY_PROFILE: dict[str, ConversationListSchema] = {
    "me2_ot": ConversationListSchema(entry_head_i32=3, reply_head_i32=3, speaker_head_i32=3),
    "le2": ConversationListSchema(entry_head_i32=3, reply_head_i32=3, speaker_head_i32=3),
    # Bootstrap defaults for close variants while profiles are refined.
    "me3_ot": ConversationListSchema(entry_head_i32=3, reply_head_i32=3, speaker_head_i32=3),
    "le3": ConversationListSchema(entry_head_i32=3, reply_head_i32=3, speaker_head_i32=3),
}


def get_schema_for_profile(profile: str) -> ConversationListSchema:
    return SCHEMA_BY_PROFILE.get(profile, ConversationListSchema(entry_head_i32=3, reply_head_i32=3, speaker_head_i32=3))
