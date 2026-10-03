"""Install a built wheel into a fresh virtualenv and smoke-test the CLI."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    printable = " ".join(command)
    print(f"+ {printable}", flush=True)
    subprocess.run(command, cwd=str(cwd), env=env, check=True)


def venv_paths(directory: Path) -> tuple[Path, Path]:
    if os.name == "nt":
        return directory / "Scripts" / "python.exe", directory / "Scripts" / "patent-troll.exe"
    return directory / "bin" / "python", directory / "bin" / "patent-troll"


def smoke_wheel(wheel: Path) -> None:
    if not wheel.exists():
        raise SystemExit(f"Wheel does not exist: {wheel}")

    with tempfile.TemporaryDirectory(prefix="patent-troll-wheel-") as temp:
        venv_dir = Path(temp) / "venv"
        initialized_dir = Path(temp) / "initialized"
        report = Path(temp) / "report.json"
        env = os.environ.copy()
        env["PATENT_TROLL_LLM_PROVIDER"] = "none"
        env["PATENT_TROLL_DEMO_FALLBACK"] = "true"

        print(f"Creating isolated venv at {venv_dir}", flush=True)
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        python, cli = venv_paths(venv_dir)

        run([str(python), "-m", "pip", "install", "--upgrade", "pip"], env=env)
        run([str(python), "-m", "pip", "install", str(wheel)], env=env)
        run(
            [
                str(python),
                "-c",
                (
                    "import importlib.util; "
                    "assert importlib.util.find_spec('openai') is None; "
                    "assert importlib.util.find_spec('anthropic') is None"
                ),
            ],
            env=env,
        )
        run([str(python), "-c", "import patent_troll; print(patent_troll.__version__)"], env=env)
        run([str(cli), "init", "--dir", str(initialized_dir), "--github-action"], env=env)
        run(
            [
                str(cli),
                "action-template",
                str(Path(temp) / "standalone-patentability.yml"),
                "--idea-file",
                "examples/idea.md",
                "--provider",
                "none",
            ],
            env=env,
        )
        run([str(cli), "doctor", "--env-file", ".env.example"], env=env)
        run([str(cli), "validate", "examples/idea.md"], env=env)
        run(
            [
                str(cli),
                "analyze",
                "examples/idea.md",
                "--provider",
                "none",
                "--format",
                "json",
                "--output",
                str(report),
            ],
            env=env,
        )

        if not report.exists() or report.stat().st_size == 0:
            raise SystemExit("Smoke report was not written")
        if not (initialized_dir / "idea.md").exists():
            raise SystemExit("Init smoke did not write idea.md")
        if not (initialized_dir / ".github" / "workflows" / "patentability.yml").exists():
            raise SystemExit("Init smoke did not write the GitHub workflow")
        if not (Path(temp) / "standalone-patentability.yml").exists():
            raise SystemExit("Action-template smoke did not write the workflow")
        print(f"Smoke report written to {report}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path, help="Path to the built .whl file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    smoke_wheel(args.wheel.resolve())


if __name__ == "__main__":
    main()
