"""Locate the llvm-mc binary shipped in this wheel."""

import os
from pathlib import Path

__all__ = ["path"]


def path() -> str:
    """Return the absolute path of the bundled llvm-mc executable."""
    exe = "llvm-mc.exe" if os.name == "nt" else "llvm-mc"
    p = Path(__file__).with_name(exe)
    if not p.is_file():
        raise FileNotFoundError(f"llvm-mc binary missing from wheel: {p}")
    return str(p)
