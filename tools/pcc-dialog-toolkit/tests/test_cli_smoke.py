import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pcc_dialog_toolkit", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_help_returns_zero() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert "pcc_dialog_extract" in result.stdout


def test_version_returns_zero() -> None:
    result = run_cli("--version")
    assert result.returncode == 0
    assert "0.1.0" in result.stdout
