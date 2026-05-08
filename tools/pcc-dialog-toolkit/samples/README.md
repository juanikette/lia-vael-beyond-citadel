# Samples Policy (PCC/TLK)

This directory is reserved for real samples used in integration tests.

## Phase 0 goal

- Prepare the structure for 1-2 known real PCC files (ME2 OT/LE2).
- Define expected names so tests and scripts are reproducible.

## Suggested convention

- `samples/me2_ot/<file>.pcc`
- `samples/le2/<file>.pcc`
- `samples/tlk/base/BIOGame_INT.tlk`

## Note

Do not commit binaries with distribution restrictions without team approval.
If they are not versioned, document equivalent local paths in tests.
