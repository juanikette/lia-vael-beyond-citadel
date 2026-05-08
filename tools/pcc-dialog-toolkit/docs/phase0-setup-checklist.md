# Phase 0 - Setup checklist

This checklist captures the minimum setup and smoke verification for a fresh local environment.

## 1) Prepare local environment

- Use Python `3.11+`.
- Create/activate a virtual environment.
- Install dependencies from `pyproject.toml`.

Example:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
```

## 2) Verify repository structure

Confirm these directories exist:

- `src/`
- `tests/`
- `docs/`
- `samples/`

## 3) Verify CLI availability

From `tools/pcc-dialog-toolkit/`, run:

```bash
PYTHONPATH=src python -m cli --help
PYTHONPATH=src python -m cli --version
```

Expected:

- Help text renders without errors.
- Version command returns `pcc-dialog-toolkit 0.1.0`.

## 4) Run smoke tests

```bash
python -m pytest tests/test_cli_smoke.py tests/test_phase0_contract.py
```

Expected:

- All tests pass.

## 5) Record baseline

Log in Notion:

- executed commands,
- pass/fail status,
- local environment notes (Python version, OS, shell).

## Reference notes (from execution log)

- Initial Phase 0 verification in Notion recorded successful `--help`, `--version`, and early pytest smoke pass.
