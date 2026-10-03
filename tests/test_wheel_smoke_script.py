import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_wheel_smoke_script_has_help() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "smoke_wheel_install.py"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Install a built wheel into a fresh virtualenv" in result.stdout
    assert "wheel" in result.stdout
