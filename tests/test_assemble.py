"""Encoding probes for the bundled llvm-mc, one set per target.

Expected bytes captured on 2026-10-28 from the system llvm-mc-23 (23.1.4).
Note: `vmovdqu zmm0, ...` does not parse in LLVM Intel syntax; the 32-bit
element form `vmovdqu32` assembles the same opcode.

If the wheel was built without a target (see LLVM_TARGETS_TO_BUILD in
CMakeLists.txt) its cases fail with a non-zero exit from llvm-mc.
"""

import re
import subprocess

import pytest

from simdref_llvm_mc import path

# (triple, mattr, extra args, source line, expected encoding bytes)
CASES = [
    ("aarch64", "+sve2,+sme2", [], "ld1b {z0.b, z1.b}, pn8/z, [x0]",
     [0x00, 0x00, 0x40, 0xa0]),
    ("aarch64", "+sve2,+sme2", [], "mov w0, #-65536",
     [0xE0, 0xFF, 0xBF, 0x52]),
    ("aarch64", "+sve2,+sme2", [], "add x0, x1, w2, uxtw #2",
     [0x20, 0x48, 0x22, 0x8B]),
    ("x86_64", "", [], "movzbl (%rdx), %eax",
     [0x0F, 0xB6, 0x02]),
    ("x86_64", "+avx512f", ["-x86-asm-syntax=intel"],
     "vmovdqu32 zmm0, zmmword ptr [rdx]",
     [0x62, 0xF1, 0x7E, 0x48, 0x6F, 0x02]),
    ("riscv64", "+zba,+v", [], "sh1add a0, a1, a2",
     [0x33, 0xA5, 0xC5, 0x20]),
    ("riscv64", "+zba,+v", [], "vle32.v v0, (a0)",
     [0x07, 0x60, 0x05, 0x02]),
]


def case_id(c):
    return f"{c[0]}-{c[3][:24]}"


@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_encoding(case):
    triple, mattr, extra, src, expected = case
    cmd = [path(), f"-triple={triple}"]
    if mattr:
        cmd.append(f"-mattr={mattr}")
    cmd += [*extra, "-show-encoding"]
    out = subprocess.run(cmd, input=src, capture_output=True, text=True)
    assert out.returncode == 0, f"{triple}: {out.stderr.strip()}"
    m = re.search(r"encoding: \[([^\]]+)\]", out.stdout)
    assert m, f"{triple}: no encoding line in {out.stdout!r}"
    got = [int(b, 16) for b in m.group(1).split(",")]
    assert got == expected
