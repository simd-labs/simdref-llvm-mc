"""Locate the binaries shipped in this wheel."""

import os
from pathlib import Path

__all__ = ["path"]


def path(name: str = "llvm-mc") -> str:
    """Return the absolute path of the bundled executable `name` (llvm-mc or xed)."""
    exe = f"{name}.exe" if os.name == "nt" else name
    p = Path(__file__).with_name(exe)
    if not p.is_file():
        raise FileNotFoundError(f"{name} binary missing from wheel: {p}")
    return str(p)
