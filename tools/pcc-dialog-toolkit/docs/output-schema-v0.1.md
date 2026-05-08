# Output JSON Schema v0.1 (MVP)

This document defines the output contract for `output.json`.

## Envelope

```json
{
  "schema_version": "0.1",
  "tool_version": "0.1.0",
  "input": {
    "package_path": "string",
    "game": "me1|me2|me3|le1|le2|le3"
  },
  "conversations": [],
  "errors": []
}
```

## Conversation

```json
{
  "id": "string",
  "export_index": 0,
  "package_path": "string",
  "entries": [],
  "replies": [],
  "speakers": []
}
```

## EntryNode

```json
{
  "id": 0,
  "speaker_id": null,
  "speaker_tag": null,
  "listener_tag": null,
  "line_strref": null,
  "line_text": null,
  "reply_links": []
}
```

## ReplyNode

```json
{
  "id": 0,
  "line_strref": null,
  "line_text": null,
  "target_entry_id": null,
  "condition_refs": []
}
```

## Speaker

```json
{
  "id": 0,
  "tag": null,
  "display_name": null
}
```

## Error object

```json
{
  "conversation_id": "string|null",
  "export_index": 0,
  "message": "string"
}
```
