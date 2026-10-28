"""Console entry point: run the bundled llvm-mc with the given arguments."""

import os
import sys

from . import path


def main() -> None:
    argv = [path(), *sys.argv[1:]]
    if os.name == "nt":
        # os.execv replaces the process badly on Windows; spawn instead.
        import subprocess

        raise SystemExit(subprocess.call(argv))
    os.execv(argv[0], argv)


if __name__ == "__main__":
    main()
