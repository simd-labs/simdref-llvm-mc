"""Console entry points: run the bundled llvm-mc or xed with the given arguments."""

import os
import sys

from . import path


def _run(name: str) -> None:
    argv = [path(name), *sys.argv[1:]]
    if os.name == "nt":
        # os.execv replaces the process badly on Windows; spawn instead.
        import subprocess

        raise SystemExit(subprocess.call(argv))
    os.execv(argv[0], argv)


def main() -> None:
    _run("llvm-mc")


def main_xed() -> None:
    _run("xed")


if __name__ == "__main__":
    main()
