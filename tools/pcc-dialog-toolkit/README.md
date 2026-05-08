# pcc-dialog-toolkit

MVP toolkit for extracting `BioConversation` dialogue from Mass Effect `.pcc` files (OT/LE).

## Code structure

- Source code lives directly in `src/` (no `src/pcc_dialog_toolkit/` subpackage).
- Main modules:
  - `src/cli.py`
  - `src/pcc/`
  - `src/dialogue/`
  - `src/tlk/`
  - `src/serialize/`
  - `src/model/`

## What the tool does

- Reads Mass Effect `.pcc` packages and detects `BioConversation` exports.
- Extracts dialogue stubs (`entries`, `replies`, `speakers`) as JSON.
- Resolves `StrRef` values using a base TLK and optional DLC overrides.
- Produces versioned JSON output with warning and error summaries.
- Supports strict validation so the CLI can be used as an automated gate.

## Scope and limitations

- Supports OT/LE profiles focused on `BioConversation` parsing.
- Requires `lzallright` for compressed OT PCC files (LZO).
- In resilient mode, per-conversation failures are reported without aborting the full file.
- Unknown profile/schema mismatches are flagged with `needs_schema_review`.

## Usage

```bash
pcc_dialog_extract path/to/file.pcc --list-bioconversations
pcc_dialog_extract path/to/file.pcc --inspect-bioconversation-properties
pcc_dialog_extract path/to/file.pcc --dump-bioconversation-stub --pretty
pcc_dialog_extract path/to/file.pcc --dump-bioconversation-row-payloads --pretty
pcc_dialog_extract path/to/file.pcc --validate-bioconversation-stubs --pretty
pcc_dialog_extract path/to/file.pcc --validate-bioconversation-stubs --strict-validation
pcc_dialog_extract path/to/file.pcc --phase3-report reports/phase3-sample.json --pretty
pcc_dialog_extract --phase3-batch-dir samples/me2_ot --phase3-batch-glob "*.pcc" --phase3-batch-report reports/phase3-batch-me2ot.json --pretty
pcc_dialog_extract path/to/file.pcc --dump-bioconversation-stub --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC" --pretty
pcc_dialog_extract path/to/file.pcc --game me2 --tlk ".../BIOGame_INT.tlk" --dlc-dir ".../BioGame/DLC" --output output.json --pretty
```

For local development without installing the script (from `tools/pcc-dialog-toolkit/`):

```bash
PYTHONPATH=src python -m cli --help
PYTHONPATH=src python -m cli --version
```

When `--dump-bioconversation-stub` is used with `--tlk`, the CLI resolves `line_text` for `EntryNode` and `ReplyNode`.
When `--dlc-dir` is provided, DLC TLKs are loaded by priority (`MountPriority`) and may override base TLK strings.
By default, the resolver ignores test TLKs (`*_Test_INT.tlk`) to prioritize runtime content.

When `--output` is used, the CLI writes versioned output (`schema_version`) that includes:

- successfully parsed `conversations`
- per-conversation `errors` (without aborting the full file)
- aggregate `summary` counts and warning totals

The CLI validates a minimal output contract before writing files (required top-level fields and consistent summary counts).
If warnings or conversation-level errors are present, it also prints them to the console for immediate traceability.

`--validate-bioconversation-stubs` marks `needs_schema_review=true` when the profile is unknown or parsing suggests a schema mismatch.

## JSON output (summary)

`--output` includes:

- `schema_version`
- `tool_version`
- `input`
- `summary`
- `conversations`
- `errors`
