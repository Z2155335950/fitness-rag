from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(*command: str) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("APP_SECRET_KEY", "local-check-only")
    run(
        sys.executable,
        "-m",
        "compileall",
        "-q",
        "app.py",
        "src",
        "tests",
        "data/eval",
    )
    run(
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-v",
    )
    run(sys.executable, "-m", "pip", "check")


if __name__ == "__main__":
    main()
